#!/usr/bin/env python2

import numpy as np
import cv2
import rospy
from sensor_msgs.msg import Image
import time
import cv_bridge
import math
from submarine_msgs_srvs.msg import Detections
import argparse


def detect_buoys ():
    '''
    Detects buoys in the water. Just looks for white and throws a bounding box around it.
    This can't detect which face we're looking at.
    '''
    pass

def midpoint (p1, p2):
    return p1[0] + p2[0] * 0.5, p1[1] + p2[1] * 0.5

def distance (p1, p2):
    return math.sqrt(((p2[0] - p1[0]) ** 2) + ((p2[1] - p1[1]) ** 2))

def raw_img_callback(msg):
    img = bridge.imgmsg_to_cv2(msg)

    # print('image received', time.time())

    # BGR values
    buoy_white_lower = np.array([200, 200, 75])
    buoy_white_upper = np.array([255, 255, 255])

    #get posts
    mask = cv2.inRange(img, buoy_white_lower, buoy_white_upper)

    mask = cv2.erode(mask, None, iterations=2)
    mask = cv2.dilate(mask, None, iterations=2)

    # get contours
    c_img, contours, hierarchy = cv2.findContours(mask.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)



    # check which contours we want and convert to rectangles
    rects = []
    for c in contours:
        if cv2.contourArea(c) < 3000:
            continue

        #top left point, plus width and height
        (x, y, w, h) = cv2.boundingRect(c)

        #double-check rectangle proportions to make sure there's nothing screwy going on
        if h > w and h < 4 * w:
            rects.append([x, y, w + x, h + y])
            cv2.rectangle(img, (x,y), (x+w,y+h), (0, 128, 255), 2)

    img_h, img_w, img_chan = img.shape

    #convert to neural network coordinate system 
    #top left of img is origin, bottom right is (1, 1)
    for r in rects:
        r[0] = r[0] / img_w
        r[1] = r[1] / img_h
        r[2] = r[2] / img_w
        r[3] = r[3] / img_h

    #publish image & detection
    img_msg = bridge.cv2_to_imgmsg(img)
    img_pub.publish(img_msg)

    detections_msg = Detections()
    detections_msg.detected = [0]

    for rect in rects:
        detections_msg.scores.append(1.0)
        detections_msg.boxes.append(rect)
        detections_msg.classes.append(args.class_num)
        detections_msg.detected[0] += 1
    
    det_pub.publish(detections_msg)

    if args.show or args.debug:
        cv2.imshow('buoy_detector', img)
        cv2.waitKey(1)

    if args.debug:
        cv2.imshow('buoy_contours', c_img)
        cv2.waitKey(1)

    print('image processed', time.time())

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="This script gets a bounding box from a buoy. Intended to be used for testing.")
    parser.add_argument('-c', '--camera', default='0', type=int, help='int indicating to get images from front camera (0) or bottom camera (1). Default is 0')
    parser.add_argument('-n', '--class_num', default=3, type=int, help="index of class that will be returned (default is 3, which is the jiangshi)")
    parser.add_argument('-b', '--bottom', action='store_true', help='send images on bottom camera topic instead of front camera topic')
    parser.add_argument('-s', '--show', action='store_true', help='display images locally with opencv')
    parser.add_argument('-d', '--debug', action='store_true', help='print more and display all bounding boxes locally')
    parser.add_argument('-min_iou', type=float, default=0.5, help='minimum intersection over union between boxes before they\'re considered the same. Default is .5')

    args = parser.parse_args()

    if args.bottom:
        img_pub = rospy.Publisher('bottom_network_imgs', Image, queue_size=1)
        det_pub = rospy.Publisher('bottom_network_output', Detections, queue_size=1)
    else:
        img_pub = rospy.Publisher('front_network_imgs', Image, queue_size=1)
        det_pub = rospy.Publisher('front_network_output', Detections, queue_size=1)

    bridge = cv_bridge.CvBridge()

    if args.camera == 1: 
        rospy.Subscriber('bottom_raw_imgs', Image, raw_img_callback, queue_size=1)
    else:
        rospy.Subscriber('front_raw_imgs', Image, raw_img_callback, queue_size=1)

    print('started')

    rospy.init_node('buoy_detector', anonymous=True)
    rospy.spin()

detect_buoys()