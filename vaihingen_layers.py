from __future__ import division
import caffe

import numpy as np
from PIL import Image
import random
import os

class VaihingenSegDataLayer(caffe.Layer):
    """
    Load (input image, label image) pairs from Vaihingen
    one-at-a-time while reshaping the net to preserve dimensions.

    Use this to feed data to a fully convolutional network.
    """
    def setup(self, bottom, top):
        """
        Setup data layer according to parameters:

        - vai_dir: path to PASCAL VOC year dir
        - split: train / val / test
        - mean: tuple of mean values to subtract
        - randomize: load in random order (default: True)
        - seed: seed for randomization (default: None / current time)

        for PASCAL VOC semantic segmentation.

        example
        params = dict(vai_dir="/home/ubuntu/fcn.berkeleyvision.org/data/pascal/VOC2012",
            mean=(104.00698793, 116.66876762, 122.67891434),
            split="val")
        """
        # config
        params = eval(self.param_str)
        self.vai_dir = params['vai_dir']
        self.split = params['split']
        self.mean = np.array(params['mean'])
        self.random = params.get('randomize', True)
        self.seed = params.get('seed', None)

        # two tops: data and label
        if len(top) != 2:
            raise Exception("Need to define two tops: data and label.")
        # data layers have no bottoms
        if len(bottom) != 0:
            raise Exception("Do not define a bottom.")

        # load indices for images and labels
        split_f  = '{}/{}.txt'.format(self.vai_dir,
                self.split)
        self.indices = open(split_f, 'r').read().splitlines()
        self.idx = 0

        # make eval deterministic
        if 'train' not in self.split:
            self.random = False

        # randomization: seed and pick
        if self.random:
            random.seed(self.seed)
            self.idx = random.randint(0, len(self.indices)-1)
        """
        Lables for ISPRS 2D Semantic Labelling
        0. Impervious surfaces (RGB: 255, 255, 255)
        1. Bilding (RGB: 0, 0, 255)
        2. Low vegetation (RGB: 0, 255, 255)
        3. Tree (RGB: 0, 255, 0)
        4. Car (RGB: 255, 255, 0)
        5. Clutter/background (RGB: 255, 0, 0)
        """
        self.color2index = {
            (255, 255, 255) : 0,
            (0,     0, 255) : 1,
            (0,   255, 255) : 2,
            (0,   255,   0) : 3,
            (255, 255,   0) : 4,
            (255,   0,   0) : 5
        }

        self.index2color = {
            0 : (255, 255, 255),
            1 : (0,     0, 255),
            2 : (0,   255, 255),
            3 : (0,   255,   0),
            4 : (255, 255,   0),
            5 : (255,   0,   0)
        }

    def reshape(self, bottom, top):
        # load image + label image pair
        self.data = self.load_image(self.indices[self.idx])
        self.label = self.load_label(self.indices[self.idx])
        # reshape tops to fit (leading 1 is for batch dimension)
        top[0].reshape(1, *self.data.shape)
        top[1].reshape(1, *self.label.shape)


    def forward(self, bottom, top):
        # assign output
        top[0].data[...] = self.data
        top[1].data[...] = self.label

        # pick next input
        if self.random:
            self.idx = random.randint(0, len(self.indices)-1)
        else:
            self.idx += 1
            if self.idx == len(self.indices):
                self.idx = 0


    def backward(self, top, propagate_down, bottom):
        pass


    def load_image(self, idx):
        """
        Load input image and preprocess for Caffe:
        - cast to float
        - switch channels RGB -> BGR
        - subtract mean
        - transpose to channel x height x width order
        """
        im = Image.open('{}/top_crop/{}'.format(self.vai_dir, idx))
        in_ = np.array(im, dtype=np.float32)
        in_ = in_[:,:,::-1]
        in_ -= self.mean
        in_ = in_.transpose((2,0,1))
        return in_


    def load_label(self, idx):
        """
        Load label image as 1 x height x width integer array of label indices.
        The leading singleton dimension is required by the loss.
        """
        name = '{}/gts_crop/{}'.format(self.vai_dir, idx)
        if os.path.isfile(name + '.npy'):
            label = np.load(name + '.npy')
        else:
            im = np.array(Image.open(name))
            label =  self.im2index(im)[np.newaxis, ...]
            np.save(name + '.npy', label)
        return label


    def im2index(self, im):
        """
        Lables for ISPRS 2D Semantic Labelling
        0. Impervious surfaces (RGB: 255, 255, 255)
        1. Bilding (RGB: 0, 0, 255)
        2. Low vegetation (RGB: 0, 255, 255)
        3. Tree (RGB: 0, 255, 0)
        4. Car (RGB: 255, 255, 0)
        5. Clutter/background (RGB: 255, 0, 0)
        """
        width, height, ch = im.shape
        assert len(im.shape) == 3
        assert ch == 3

        m_lable = np.zeros((width, height), dtype=np.uint8)
        for w in range(width):
            for h in range(height):
                r, g, b = im[w, h, :]
                m_lable[w, h] = self.color2index[(r, g, b)]

        return m_lable
