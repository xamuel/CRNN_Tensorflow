#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 17-9-25 下午3:56
# @Author  : Luo Yao
# @Site    : http://github.com/TJCVRS
# @File    : test_shadownet.py
# @IDE: PyCharm Community Edition
"""
Test shadow net script
"""
import os
import os.path as ops
import tensorflow as tf
import matplotlib.pyplot as plt
import argparse
import numpy as np
import math

from local_utils import data_utils
from crnn_model import crnn_model
from global_configuration import config


def init_args():
    """

    :return:
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--dataset_dir', type=str, required=True,
                        help='Path to test tfrecords data')
    parser.add_argument('-w', '--weights_path', type=str, required=True,
                        help='Path to pre-trained weights')
    parser.add_argument('-r', '--is_recursive', type=bool,
                        help='Whether to recursively test the dataset')
    parser.add_argument('-c', '--num_classes', type=int, required=True,
                        help='Force number of character classes to this number. '
                             'Use 37 to run with the demo data.')
    parser.add_argument('-j', '--num_threads', type=int, default=int(os.cpu_count() / 2),
                        help='Number of threads to use in batch shuffling')

    return parser.parse_args()


def test_shadownet(dataset_dir: str, weights_path: str, is_vis: bool = False,
                   is_recursive: bool = True, num_threads: int = 4,
                   num_classes: int = None):
    """

    :param dataset_dir:
    :param weights_path:
    :param is_vis:
    :param is_recursive:
    :param num_threads:
    :param num_classes:
    """
    # Initialize the record decoder
    decoder = data_utils.TextFeatureIO().reader
    images_t, labels_t, imagenames_t = decoder.read_features(
        ops.join(dataset_dir, 'test_feature.tfrecords'), num_epochs=None)
    if not is_recursive:
        images_sh, labels_sh, imagenames_sh = tf.train.shuffle_batch(tensors=[images_t, labels_t, imagenames_t],
                                                                     batch_size=config.cfg.TEST.BATCH_SIZE,
                                                                     capacity=1000 + 2 * config.cfg.TEST.BATCH_SIZE,
                                                                     min_after_dequeue=2, num_threads=num_threads)
    else:
        images_sh, labels_sh, imagenames_sh = tf.train.batch(tensors=[images_t, labels_t, imagenames_t],
                                                             batch_size=config.cfg.TEST.BATCH_SIZE,
                                                             capacity=1000 + 2 * config.cfg.TEST.BATCH_SIZE,
                                                             num_threads=num_threads)

    images_sh = tf.cast(x=images_sh, dtype=tf.float32)

    # build shadownet
    num_classes = len(decoder.char_dict) + 1 if num_classes is None else num_classes
    net = crnn_model.ShadowNet(phase='Test', hidden_nums=config.cfg.ARCH.HIDDEN_UNITS,
                               layers_nums=config.cfg.ARCH.HIDDEN_LAYERS,
                               num_classes=num_classes)

    with tf.variable_scope('shadow'):
        net_out = net.build_shadownet(inputdata=images_sh)

    decoded, _ = tf.nn.ctc_beam_search_decoder(net_out,
                                               config.cfg.ARCH.SEQ_LENGTH * np.ones(config.cfg.TEST.BATCH_SIZE),
                                               merge_repeated=False)

    # config tf session
    sess_config = tf.ConfigProto()
    sess_config.gpu_options.per_process_gpu_memory_fraction = config.cfg.TRAIN.GPU_MEMORY_FRACTION
    sess_config.gpu_options.allow_growth = config.cfg.TRAIN.TF_ALLOW_GROWTH

    # config tf saver
    saver = tf.train.Saver()

    sess = tf.Session(config=sess_config)

    test_sample_count = 0
    for record in tf.python_io.tf_record_iterator(ops.join(dataset_dir, 'test_feature.tfrecords')):
        test_sample_count += 1
    loops_nums = int(math.ceil(test_sample_count / config.cfg.TEST.BATCH_SIZE))
    # loops_nums = 100

    with sess.as_default():

        # restore the model weights
        saver.restore(sess=sess, save_path=weights_path)

        coord = tf.train.Coordinator()
        threads = tf.train.start_queue_runners(sess=sess, coord=coord)

        print('Start predicting ......')
        if not is_recursive:
            predictions, images, labels, imagenames = sess.run([decoded, images_sh, labels_sh, imagenames_sh])
            imagenames = np.reshape(imagenames, newshape=imagenames.shape[0])
            imagenames = [tmp.decode('utf-8') for tmp in imagenames]
            preds_res = decoder.sparse_tensor_to_str(predictions[0])
            gt_res = decoder.sparse_tensor_to_str(labels)

            accuracy = []

            for index, gt_label in enumerate(gt_res):
                pred = preds_res[index]
                totol_count = len(gt_label)
                correct_count = 0
                try:
                    for i, tmp in enumerate(gt_label):
                        if tmp == pred[i]:
                            correct_count += 1
                except IndexError:
                    continue
                finally:
                    try:
                        accuracy.append(correct_count / totol_count)
                    except ZeroDivisionError:
                        if len(pred) == 0:
                            accuracy.append(1)
                        else:
                            accuracy.append(0)

            accuracy = np.mean(np.array(accuracy).astype(np.float32), axis=0)
            print('Mean test accuracy is {:5f}'.format(accuracy))

            for index, image in enumerate(images):
                print('Predict {:s} image with gt label: {:s} **** predict label: {:s}'.format(
                    imagenames[index], gt_res[index], preds_res[index]))
                if is_vis:
                    plt.imshow(image[:, :, (2, 1, 0)])
                    plt.show()
        else:
            accuracy = []
            for epoch in range(loops_nums):
                predictions, images, labels, imagenames = sess.run([decoded, images_sh, labels_sh, imagenames_sh])
                imagenames = np.reshape(imagenames, newshape=imagenames.shape[0])
                imagenames = [tmp.decode('utf-8') for tmp in imagenames]
                preds_res = decoder.sparse_tensor_to_str(predictions[0])
                gt_res = decoder.sparse_tensor_to_str(labels)

                for index, gt_label in enumerate(gt_res):
                    pred = preds_res[index]
                    totol_count = len(gt_label)
                    correct_count = 0
                    try:
                        for i, tmp in enumerate(gt_label):
                            if tmp == pred[i]:
                                correct_count += 1
                    except IndexError:
                        continue
                    finally:
                        try:
                            accuracy.append(correct_count / totol_count)
                        except ZeroDivisionError:
                            if len(pred) == 0:
                                accuracy.append(1)
                            else:
                                accuracy.append(0)

                for index, image in enumerate(images):
                    print('Predict {:s} image with gt label: {:s} **** predict label: {:s}'.format(
                        imagenames[index], gt_res[index], preds_res[index]))
                    # if is_vis:
                    #     plt.imshow(image[:, :, (2, 1, 0)])
                    #     plt.show()

            accuracy = np.mean(np.array(accuracy).astype(np.float32), axis=0)
            print('Test accuracy is {:5f}'.format(accuracy))

        coord.request_stop()
        coord.join(threads=threads)

    sess.close()
    return


if __name__ == '__main__':
    # init args
    args = init_args()

    # test shadow net
    test_shadownet(args.dataset_dir, args.weights_path, args.is_recursive, args.num_threads, args.num_classes)
