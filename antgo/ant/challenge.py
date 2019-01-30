# -*- coding: UTF-8 -*-
# @Time    : 17-5-9
# @File    : challenge.py
# @Author  : jian<jian@mltalker.com>
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from antgo.resource.html import *
from antgo.ant.base import *
from antgo.dataflow.common import *
from antgo.measures.statistic import *
from antgo.task.task import *
from antgo.utils import logger
from antgo.dataflow.recorder import *
from antgo.measures.deep_analysis import *
from antgo.measures.significance import *
import shutil
import tarfile
from datetime import datetime
from antgo.measures import *

class AntChallenge(AntBase):
  def __init__(self, ant_context,
               ant_name,
               ant_data_folder,
               ant_dump_dir,
               ant_token,
               ant_task_config=None,
               ant_task_benchmark=None,
               **kwargs):
    super(AntChallenge, self).__init__(ant_name, ant_context, ant_token, **kwargs)
    self.ant_data_source = ant_data_folder
    self.ant_dump_dir = ant_dump_dir
    self.ant_context.ant = self
    self.ant_task_config = ant_task_config
    self.ant_task_benchmark = ant_task_benchmark
    self.context.devices = [int(d) for d in kwargs.get('devices', '').split(',') if d != '']

  def start(self):
    # 0.step loading challenge task
    running_ant_task = None
    if self.token is not None:
      # 0.step load challenge task
      challenge_task_config = self.rpc("TASK-CHALLENGE")
      if challenge_task_config is None:
        # invalid token
        logger.error('couldnt load challenge task')
        self.token = None
      elif challenge_task_config['status'] == 'SUSPEND':
        # prohibit submit challenge task frequently
        # submit only one in one week
        logger.error('prohibit submit challenge task frequently')
        exit(-1)
      elif challenge_task_config['status'] == 'OK':
        # maybe user token or task token
        if 'task' in challenge_task_config:
          challenge_task = create_task_from_json(challenge_task_config)
          if challenge_task is None:
            logger.error('couldnt load challenge task')
            exit(-1)
          running_ant_task = challenge_task
      else:
        # unknow error
        logger.error('unknow error')
        exit(-1)

    if running_ant_task is None:
      # 0.step load custom task
      custom_task = create_task_from_xml(self.ant_task_config, self.context)
      if custom_task is None:
        logger.error('couldnt load custom task')
        exit(0)
      running_ant_task = custom_task

    assert (running_ant_task is not None)

    # running position
    if self.running_platform == 'p2p':
      # 1.step pack codebase
      codebase_address, codebase_address_code = self.package_codebase()

      if codebase_address is None:
        logger.error('couldnt package whole codebase')
        return

      # 2.step apply computing pow
      max_running_time = 0.0    # unit hour
      computing_pow = {}
      if FLAGS.order_id() == '':
        # transform max time unit
        max_running_time_and_unit = FLAGS.max_time()
        max_running_time = float(max_running_time_and_unit[0:-1])
        max_running_time_unit = max_running_time_and_unit[-1]
        if max_running_time_unit == 's':
          # second
          max_running_time = max_running_time / (60.0 * 60.0)
        elif max_running_time_unit == 'm':
          max_running_time = max_running_time / 60.0
        elif max_running_time_unit == 'd':
          max_running_time = max_running_time * 24
        elif max_running_time_unit == 'h':
          pass
        else:
          logger.error('max running time error')
          return

        computing_pow = self.subgradient_rpc.make_computingpow_order(max_running_time,
                                                                     self.running_config['OS_PLATFORM'],
                                                                     self.running_config['OS_VERSION'],
                                                                     self.running_config['SOFTWARE_FRAMEWORK'],
                                                                     self.running_config['CPU_MODEL'],
                                                                     self.running_config['CPU_NUM'],
                                                                     self.running_config['CPU_MEM'],
                                                                     self.running_config['GPU_MODEL'],
                                                                     self.running_config['GPU_NUM'],
                                                                     self.running_config['GPU_MEM'],
                                                                     running_ant_task.dataset_name,
                                                                     FLAGS.max_fee())
        if computing_pow is None:
          logger.error('fail to find matched computing pow')
          return

        logger.info('success to apply computing pow order %s (%s:(rpc)%s or (ssh)%s)'%(computing_pow['order_id'],
                                                                                       computing_pow['order_ip'],
                                                                                       str(computing_pow['order_rpc_port']),
                                                                                       str(computing_pow['order_ssh_port'])))
      else:
        computing_pow = {'order_id': FLAGS.order_id(),
                         'order_ip': FLAGS.order_ip(),
                         'order_rpc_port': FLAGS.order_rpc_port(),
                         'order_ssh_port': FLAGS.order_ssh_port()}

        if computing_pow['order_ip'] == '' or computing_pow['order_rpc_port'] == 0:
          logger.error('order_ip is empty or order_rpc_port is empty')
          return

      # 3.step exchange access token
      secret, signature = self.subgradient_rpc.signature(computing_pow['order_id'])
      result = self.subgradient_rpc.authorize(computing_pow['order_ip'],
                                              computing_pow['order_rpc_port'],
                                              order_id=computing_pow['order_id'],
                                              secret=secret,
                                              signature=signature)

      if result['authorize'] != 'success':
        logger.error('couldnt authorize order access token')
        return

      order_access_token = result['access_token']
      order_launch_time = result['launch_time']
      order_rental_time = result['rental_time']

      logger.info('computing pow rental time is %0.2f Hour, its expire time is %s'%(order_rental_time,
                                                                                    time.strftime('%Y-%m-%d %H:%M:%S',
                                                                                                  time.localtime(order_launch_time + order_rental_time * 60 * 60))))

      remote_cmd = ''
      if self.app_token is not None:
        remote_cmd = 'antgo challenge --main_file=%s --main_param=%s --running_platform=local --token=%s --max_time=%s'%(
          self.main_file, self.main_param, self.app_token, '%fh'%(max_running_time - 0.5))
      else:
        remote_cmd = 'antgo challenge --main_file=%s --main_param=%s --running_platform=local --task=%s --max_time=%s'%(
          self.main_file, self.main_param, FLAGS.task(), '%fh'%(max_running_time - 0.5))

      if FLAGS.from_experiment() is not None:
        remote_cmd += ' --from_experiment=%s'%FLAGS.from_experiment()
      self.subgradient_rpc.launch(computing_pow['order_ip'],
                                  computing_pow['order_rpc_port'],
                                  access_token=order_access_token,
                                  cmd=remote_cmd,
                                  code_address=codebase_address,
                                  code_address_code=codebase_address_code)

      while True:
        time.sleep(5)
        status_response = self.subgradient_rpc.status(computing_pow['order_ip'],
                                                      computing_pow['order_rpc_port'],
                                                      access_token=order_access_token)

        if result['authorize'] == 'fail':
          # try refresh access token
          refresh_result = self.subgradient_rpc.refresh(computing_pow['order_ip'],
                                                        computing_pow['order_rpc_port'],
                                                        access_token=order_access_token)

          if refresh_result['authorize'] == 'fail':
            logger.error('%s on computing pow server'%refresh_result['reason'])
            return

          order_access_token = refresh_result['refresh_access_token']
        else:
          logger.info('computing pow order is %s'%status_response['result'])

          if status_response['result'] == 'running':
            logger.info('you can access computing pow by \"ssh -p %d %s@%s\"'%(int(computing_pow['order_ssh_port']),
                                                                               computing_pow['order_id'],
                                                                               computing_pow['order_ip']))
            return

    # now time stamp
    now_time_stamp = datetime.fromtimestamp(self.time_stamp).strftime('%Y%m%d.%H%M%S.%f')

    # # ############
    # ss = AntYesNoCrowdsource(running_ant_task)
    # cc = RecordReader('/Users/jian/PycharmProjects/antgo/antgo/dump/20180726.151520.620675/record')
    # ss.dump_dir = "/Users/jian/Downloads/mm/"
    # ss.experiment_id = '20180726.151520.620675'
    # ss.app_token = self.token
    # ss.crowdsource_server(cc)
    # ############
    #
    # time.sleep(100000)

    # 0.step warp model (main_file and main_param)
    self.stage = 'CHALLENGE-MODEL'
    # - backup in dump_dir
    main_folder = self.main_folder
    main_param = FLAGS.main_param()
    main_file = FLAGS.main_file()

    if not os.path.exists(os.path.join(self.ant_dump_dir, now_time_stamp)):
      os.makedirs(os.path.join(self.ant_dump_dir, now_time_stamp))

    goldcoin = os.path.join(self.ant_dump_dir, now_time_stamp, '%s-goldcoin.tar.gz' % self.ant_name)

    if os.path.exists(goldcoin):
      os.remove(goldcoin)

    tar = tarfile.open(goldcoin, 'w:gz')
    tar.add(os.path.join(main_folder, main_file), arcname=main_file)
    if main_param is not None:
      tar.add(os.path.join(main_folder, main_param), arcname=main_param)
    tar.close()

    # - backup in cloud
    if os.path.exists(goldcoin):
      file_size = os.path.getsize(goldcoin) / 1024.0
      if file_size < 500:
        if not PY3 and sys.getdefaultencoding() != 'utf8':
          reload(sys)
          sys.setdefaultencoding('utf8')
        # model file shouldn't too large (500KB)
        with open(goldcoin, 'rb') as fp:
          self.context.job.send({'DATA': {'MODEL': fp.read()}})

    # 1.step loading test dataset
    logger.info('loading test dataset %s'%running_ant_task.dataset_name)
    ant_test_dataset = running_ant_task.dataset('test',
                                                os.path.join(self.ant_data_source, running_ant_task.dataset_name),
                                                running_ant_task.dataset_params)

    with safe_recorder_manager(ant_test_dataset):
      # split data and label
      data_annotation_branch = DataAnnotationBranch(Node.inputs(ant_test_dataset))
      self.context.recorder = RecorderNode(Node.inputs(data_annotation_branch.output(1)))

      self.stage = "CHALLENGE"
      logger.info('start infer process')
      infer_dump_dir = os.path.join(self.ant_dump_dir, now_time_stamp, 'inference')
      if not os.path.exists(infer_dump_dir):
        os.makedirs(infer_dump_dir)
      else:
        shutil.rmtree(infer_dump_dir)
        os.makedirs(infer_dump_dir)

      intermediate_dump_dir = os.path.join(self.ant_dump_dir, now_time_stamp, 'record')
      with safe_recorder_manager(self.context.recorder):
        self.context.recorder.dump_dir = intermediate_dump_dir
        # from ablation experiment
        ablation_blocks = getattr(self.ant_context.params, 'ablation', [])
        for b in ablation_blocks:
          self.ant_context.deactivate_block(b)
          
        with performance_statistic_region(self.ant_name):
          self.context.call_infer_process(data_annotation_branch.output(0), infer_dump_dir)

      task_running_statictic = get_performance_statistic(self.ant_name)
      task_running_statictic = {self.ant_name: task_running_statictic}
      task_running_elapsed_time = task_running_statictic[self.ant_name]['time']['elapsed_time']
      task_running_statictic[self.ant_name]['time']['elapsed_time_per_sample'] = \
          task_running_elapsed_time / float(ant_test_dataset.size)

      if not self.context.recorder.is_measure:
        # has no annotation to continue to meausre
        # notify
        self.context.job.send(
          {'DATA': {'REPORT': copy.deepcopy(task_running_statictic), 'RECORD': intermediate_dump_dir}})

        # generate report resource
        logger.info('generate model evaluation report')
        everything_to_html(task_running_statictic, os.path.join(self.ant_dump_dir, now_time_stamp))
        return

      logger.info('start evaluation process')
      evaluation_measure_result = []
      with safe_recorder_manager(RecordReader(intermediate_dump_dir)) as record_reader:
        for measure in running_ant_task.evaluation_measures:
          if measure.crowdsource:
            # start crowdsource server
            measure.dump_dir = os.path.join(infer_dump_dir, measure.name, 'static')
            if not os.path.exists(measure.dump_dir):
              os.makedirs(measure.dump_dir)

            measure.experiment_id = now_time_stamp
            measure.app_token = self.token
            logger.info('launch crowdsource evaluation server')
            crowdsrouce_evaluation_status = measure.crowdsource_server(record_reader)
            if not crowdsrouce_evaluation_status:
              logger.error('couldnt finish crowdsource evaluation server')
              continue

            # using crowdsource evaluation
            result = measure.eva()
            # TODO: support bootstrap confidence interval for crowdsource evaluation
          else:
            # evaluation
            record_generator = record_reader.iterate_read('predict', 'groundtruth')
            result = measure.eva(record_generator, None)
            if measure.is_support_rank:
              # compute confidence interval
              confidence_interval = bootstrap_confidence_interval(record_reader, time.time(), measure, 1)
              result['statistic']['value'][0]['interval'] = confidence_interval

          evaluation_measure_result.append(result)


        # #########################
        # roc_auc_measure = {'statistic': {'name': 'roc_auc',
        #                                  'value': [{'name': 'ROC', 'value': [[[0, 3], [1, 0], [2, 6]],
        #                                                                      [[0, 8], [2, 3], [3, 7]]],
        #                                             'type': 'CURVE', 'x': 'FP', 'y': 'TP',
        #                                             'legend': ['class-0', 'class-1']},
        #                                            {'name': 'AUC', 'value': [0.1, 0.2], 'type': 'SCALAR', 'x': 'class',
        #                                             'y': 'AUC'}]}}
        #
        # voc_measure = {'statistic': {'name': 'voc',
        #                              'value': [{'name': 'MAP', 'value': [18.0, 9.0, 20.0], 'type': 'SCALAR', 'x': 'class',
        #                                         'y': 'Mean Average Precision'},
        #                                        {'name': 'Mean-MAP', 'value': 0.14, 'type': 'SCALAR'}]}}
        #
        #
        # evaluation_measure_result.append(roc_auc_measure)
        # evaluation_measure_result.append(voc_measure)
        # #########################

        task_running_statictic[self.ant_name]['measure'] = evaluation_measure_result
      
      # if self.is_non_mltalker_task:
      #   # generate report resource
      #   logger.info('generate model evaluation report')
      #   everything_to_html(task_running_statictic, os.path.join(self.ant_dump_dir, now_time_stamp))
      #   return

      # significance statistic
      logger.info('significance difference compare and rank')
      # benchmark record
      benchmark_model_data = {}
      if self.token is not None:
        benchmark_info = self.rpc("TASK-BENCHMARK")
        if benchmark_info is not None:
          for bmd in benchmark_info:
            benchmark_name = bmd['benchmark_name']
            benchmark_record = bmd['benchmark_record']
            benchmark_report = bmd['benchmark_report']
  
            # download benchmark record from url
            benchmark_record = self.download(benchmark_record,
                                             target_path=os.path.join(self.ant_dump_dir, now_time_stamp, 'benchmark'),
                                             target_name='%s.tar.gz'%benchmark_name,
                                             archive=benchmark_name)
  
            if 'record' not in benchmark_model_data:
              benchmark_model_data['record'] = {}
            benchmark_model_data['record'][benchmark_name] = benchmark_record
  
            if 'report' not in benchmark_model_data:
              benchmark_model_data['report'] = {}
  
            for benchmark_experiment_name, benchmark_experiment_report in benchmark_report['CHALLENGE']['REPORT'].items():
              benchmark_model_data['report'][benchmark_name] = benchmark_experiment_report
      elif self.ant_task_benchmark is not None:
        for experiment in self.ant_task_benchmark.split(','):
          if os.path.exists(os.path.join(self.ant_dump_dir, experiment)):
            if 'record' not in benchmark_model_data:
              benchmark_model_data['record'] = {}
            benchmark_model_data['record'][experiment] = os.path.join(self.ant_dump_dir, experiment, 'record')
        
      if benchmark_model_data is not None and 'record' in benchmark_model_data:
        benchmark_model_record = benchmark_model_data['record']

        task_running_statictic[self.ant_name]['significant_diff'] = {}
        for measure in running_ant_task.evaluation_measures:
          if measure.is_support_rank and not measure.crowdsource:
            significant_diff_score = []
            for benchmark_model_name, benchmark_model_address in benchmark_model_record.items():
              with safe_recorder_manager(RecordReader(intermediate_dump_dir)) as record_reader:
                with safe_recorder_manager(RecordReader(benchmark_model_address)) as benchmark_record_reader:
                  s = bootstrap_ab_significance_compare([record_reader, benchmark_record_reader], time.time(), measure, 1)

                  significant_diff_score.append({'name': benchmark_model_name, 'score': s})
            task_running_statictic[self.ant_name]['significant_diff'][measure.name] = significant_diff_score
          elif measure.is_support_rank and measure.crowdsource:
            # TODO: support model significance compare for crowdsource evaluation
            pass

      # error analysis
      logger.info('error analysis')
      # benchmark report
      benchmark_model_statistic = None
      if benchmark_model_data is not None and 'report' in benchmark_model_data:
        benchmark_model_statistic = benchmark_model_data['report']
      
      # task_running_statictic={self.ant_name:
      #                           {'measure':[
      #                             {'statistic': {'name': 'MESR',
      #                                            'value': [{'name': 'MESR', 'value': 0.4, 'type':'SCALAR'}]},
      #                                            'info': [{'id':0,'score':0.8,'category':1},
      #                                                     {'id':1,'score':0.3,'category':1},
      #                                                     {'id':2,'score':0.9,'category':1},
      #                                                     {'id':3,'score':0.5,'category':1},
      #                                                     {'id':4,'score':1.0,'category':1}]},
      #                             {'statistic': {'name': "SE",
      #                                            'value': [{'name': 'SE', 'value': 0.5, 'type': 'SCALAR'}]},
      #                                            'info': [{'id':0,'score':0.4,'category':1},
      #                                                     {'id':1,'score':0.2,'category':1},
      #                                                     {'id':2,'score':0.1,'category':1},
      #                                                     {'id':3,'score':0.5,'category':1},
      #                                                     {'id':4,'score':0.23,'category':1}]}]}}
      
      for measure_result in task_running_statictic[self.ant_name]['measure']:
        if 'info' in measure_result and len(measure_result['info']) > 0:
          measure_name = measure_result['statistic']['name']
          measure_data = measure_result['info']
          
          # independent analysis per category for classification problem
          measure_data_list = []
          if running_ant_task.class_label is not None and len(running_ant_task.class_label) > 1:
            if running_ant_task.class_label is not None:
              for cl_i, cl in enumerate(running_ant_task.class_label):
                measure_data_list.append([md for md in measure_data if md['category'] == cl or md['category'] == cl_i])
            
          if len(measure_data_list) == 0:
            measure_data_list.append(measure_data)
          
          for category_id, category_measure_data in enumerate(measure_data_list):
            if len(category_measure_data) == 0:
              continue
              
            if 'analysis' not in task_running_statictic[self.ant_name]:
              task_running_statictic[self.ant_name]['analysis'] = {}
            
            if measure_name not in task_running_statictic[self.ant_name]['analysis']:
              task_running_statictic[self.ant_name]['analysis'][measure_name] = {}
  
            # reorganize as list
            method_samples_list = [{'name': self.ant_name, 'data': category_measure_data}]
            if benchmark_model_statistic is not None:
              # extract statistic data from benchmark
              for benchmark_name, benchmark_statistic_data in benchmark_model_statistic.items():
                # finding corresponding measure
                for benchmark_measure_result in benchmark_statistic_data['measure']:
                  if benchmark_measure_result['statistic']['name'] == measure_name:
                    benchmark_measure_data = benchmark_measure_result['info']

                    # finding corresponding category
                    sub_benchmark_measure_data = None
                    if running_ant_task.class_label is not None and len(running_ant_task.class_label) > 1:
                      sub_benchmark_measure_data = \
                        [md for md in benchmark_measure_data if md['category'] == running_ant_task.class_label[category_id]]
                    if sub_benchmark_measure_data is None:
                      sub_benchmark_measure_data = benchmark_measure_data

                    method_samples_list.append({'name': benchmark_name, 'data': sub_benchmark_measure_data})

                    break
                break
  
            # reorganize data as score matrix
            method_num = len(method_samples_list)
            # samples_num are the same among methods
            samples_num = len(method_samples_list[0]['data'])
            # samples_num = ant_test_dataset.size
            method_measure_mat = np.zeros((method_num, samples_num))
            samples_map = []
  
            for method_id, method_measure_data in enumerate(method_samples_list):
              # reorder data by index
              order_key = 'id'
              if 'index' in method_measure_data['data'][0]:
                order_key = 'index'
              method_measure_data_order = sorted(method_measure_data['data'], key=lambda x: x[order_key])
              
              if method_id == 0:
                # record sample id
                for sample_id, sample in enumerate(method_measure_data_order):
                  samples_map.append(sample)

              # order consistent
              for sample_id, sample in enumerate(samples_map):
                  method_measure_mat[method_id, sample_id] = sample['score']
  
            is_binary = False
            # collect all score
            test_score = [td['score'] for td in method_samples_list[0]['data']
                                if td['score'] > -float("inf") and td['score'] < float("inf")]
            hist, x_bins = np.histogram(test_score, 100)
            if len(np.where(hist > 0.0)[0]) <= 2:
              is_binary = True

            # score matrix analysis
            if not is_binary:
              s, ri, ci, lr_samples, mr_samples, hr_samples = \
                continuous_multi_model_measure_analysis(method_measure_mat, samples_map, ant_test_dataset)
              
              analysis_tag = 'Global'
              if len(measure_data_list) > 1:
                analysis_tag = 'Global-Category-'+str(running_ant_task.class_label[category_id])
              
              model_name_ri = [method_samples_list[r]['name'] for r in ri]
              task_running_statictic[self.ant_name]['analysis'][measure_name][analysis_tag] = \
                            {'value': s,
                             'type': 'MATRIX',
                             'x': ci,
                             'y': model_name_ri,
                             'sampling': [{'name': 'High Score Region', 'data': hr_samples},
                                          {'name': 'Middle Score Region', 'data': mr_samples},
                                          {'name': 'Low Score Region', 'data': lr_samples}]}
  
              # group by tag
              tags = getattr(ant_test_dataset, 'tag', None)
              if tags is not None:
                for tag in tags:
                  g_s, g_ri, g_ci, g_lr_samples, g_mr_samples, g_hr_samples = \
                    continuous_multi_model_measure_analysis(method_measure_mat,
                                                            samples_map,
                                                            ant_test_dataset,
                                                            filter_tag=tag)
                  
                  analysis_tag = 'Group'
                  if len(measure_data_list) > 1:
                    analysis_tag = 'Group-Category-' + str(running_ant_task.class_label[category_id])

                  if analysis_tag not in task_running_statictic[self.ant_name]['analysis'][measure_name]:
                    task_running_statictic[self.ant_name]['analysis'][measure_name][analysis_tag] = []

                  model_name_ri = [method_samples_list[r]['name'] for r in g_ri]
                  tag_data = {'value': g_s,
                              'type': 'MATRIX',
                              'x': g_ci,
                              'y': model_name_ri,
                              'sampling': [{'name': 'High Score Region', 'data': g_hr_samples},
                                           {'name': 'Middle Score Region', 'data': g_mr_samples},
                                           {'name': 'Low Score Region', 'data': g_lr_samples}]}
  
                  task_running_statictic[self.ant_name]['analysis'][measure_name][analysis_tag].append((tag, tag_data))
            else:
              s, ri, ci, region_95, region_52, region_42, region_13, region_one, region_zero = \
                discrete_multi_model_measure_analysis(method_measure_mat,
                                                      samples_map,
                                                      ant_test_dataset)

              analysis_tag = 'Global'
              if len(measure_data_list) > 1:
                analysis_tag = 'Global-Category-' + str(running_ant_task.class_label[category_id])

              model_name_ri = [method_samples_list[r]['name'] for r in ri]
              task_running_statictic[self.ant_name]['analysis'][measure_name][analysis_tag] = \
                              {'value': s,
                               'type': 'MATRIX',
                               'x': ci,
                               'y': model_name_ri,
                               'sampling': [{'name': '95%', 'data': region_95},
                                            {'name': '52%', 'data': region_52},
                                            {'name': '42%', 'data': region_42},
                                            {'name': '13%', 'data': region_13},
                                            {'name': 'best', 'data': region_one},
                                            {'name': 'zero', 'data': region_zero}]}
  
              # group by tag
              tags = getattr(ant_test_dataset, 'tag', None)
              if tags is not None:
                for tag in tags:
                  g_s, g_ri, g_ci, g_region_95, g_region_52, g_region_42, g_region_13, g_region_one, g_region_zero = \
                    discrete_multi_model_measure_analysis(method_measure_mat,
                                                            samples_map,
                                                            ant_test_dataset,
                                                            filter_tag=tag)
                  # if 'group' not in task_running_statictic[self.ant_name]['analysis'][measure_name]:
                  #   task_running_statictic[self.ant_name]['analysis'][measure_name]['group'] = []
                  #
                  analysis_tag = 'Group'
                  if len(measure_data_list) > 1:
                    analysis_tag = 'Group-Category-' + str(running_ant_task.class_label[category_id])

                  if analysis_tag not in task_running_statictic[self.ant_name]['analysis'][measure_name]:
                    task_running_statictic[self.ant_name]['analysis'][measure_name][analysis_tag] = []

                  model_name_ri = [method_samples_list[r]['name'] for r in g_ri]
                  tag_data = {'value': g_s,
                              'type': 'MATRIX',
                              'x': g_ci,
                              'y': model_name_ri,
                              'sampling': [{'name': '95%', 'data': region_95},
                                           {'name': '52%', 'data': region_52},
                                           {'name': '42%', 'data': region_42},
                                           {'name': '13%', 'data': region_13},
                                           {'name': 'best', 'data': region_one},
                                           {'name': 'zero', 'data': region_zero}]}
  
                  task_running_statictic[self.ant_name]['analysis'][measure_name][analysis_tag].append((tag, tag_data))

      # notify
      self.context.job.send({'DATA': {'REPORT': copy.deepcopy(task_running_statictic)}})

      # generate report resource
      logger.info('generate model evaluation report')
      everything_to_html(task_running_statictic, os.path.join(self.ant_dump_dir, now_time_stamp))
