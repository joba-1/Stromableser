import paho.mqtt.client as mqtt
import cv2
import numpy as np
import urllib as ul
import sys
import time
from datetime import datetime

# may need tweaking to detect warp box area or digits: 
# blurr=3,5,7 and low=10-40 while low*ratio < 255 seems to work
area_blurr,  area_low,  area_ratio  = 3, 40, 5
digit_blurr, digit_low, digit_ratio = 3, 15, 15

# minimum similarity for best match
minSimilarity = 0.78

# last value, used for sanity check
lastValue = 0


def eprint(*args, **kwargs):
    """ print() to stderr """
    print(*args, file=sys.stderr, **kwargs)


def readDigits(file):
    """ read numpy compressed arrays with bw images of digits 0-9
      returns indexed images with indexes 'd0' - 'd9' """
    return np.load(file)


def meanPoint(points):
    """ calculates average position of a point lists. Returns [xAvg, yAvg] """
    return np.int0(np.mean(points[:, 0])), np.int0(np.mean(points[:, 1]))


def minSquare(plist):
    """ return nparray of 4 edge points of an uneven square, clockwise starting at upper left """
    upperLeft = meanPoint(plist[plist[:, 0] + plist[:, 1] == np.min(plist[:, 0] + plist[:, 1])])
    lowerRight = meanPoint(plist[plist[:, 0] + plist[:, 1] == np.max(plist[:, 0] + plist[:, 1])])
    upperRight = meanPoint(plist[plist[:, 0] - plist[:, 1] == np.max(plist[:, 0] - plist[:, 1])])
    lowerLeft = meanPoint(plist[plist[:, 0] - plist[:, 1] == np.min(plist[:, 0] - plist[:, 1])])

    return np.array([upperLeft, upperRight, lowerRight, lowerLeft])


def ledOn(on):
    """ switch led on or off with tasmota mqtt commands """
    client = mqtt.Client()
    try:
        client.connect('localhost', 1883)
    except:
        eprint(datetime.now(), "MQTT connect failed")
        return

    if on:
        msg = '1'
    else:
        msg = '0'

    _ = client.publish('cmnd/espcam1/power', msg)


def aquireGrayscaleImage(url):
    """ aquire image from cam """
    
    if url[:5] != "file:":
        ledOn(True)
        time.sleep(2)  # let camera adapt to brightness

    try:
        req = ul.request.urlopen(url)
    except ul.error.URLError as e:
        eprint(datetime.now(), e.__dict__)
        return None
    
    if url[:5] != "file:":
        ledOn(False)

    arr = np.asarray(bytearray(req.read()), dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)

    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


def applyEdgeFilter(img, blurr, low, ratio):
    """ return bw image with edges """
    blurred = cv2.GaussianBlur(img, (blurr, blurr), 0)
    return cv2.Canny(blurred, low, ratio * low)


def findLargestSquare(edges):
    """ find largest uneven square (the line with the digits).
    Return contour or None if not found """
    _, contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    max_area = 30*50
    max_index = None
    for index, cnt in enumerate(contours):
        _, _, bw, bh = cv2.boundingRect(cnt)
        area = bw * bh
        if area > max_area:
            max_area = area
            max_index = index
   
    if max_index is None:
        return None

    return contours[max_index]


def undoPerspectiveDistortion(img, contour):
    """ warp image to make horizontal rectangle from distorted digits,
    return horizontal cut out rectangle of digits area """

    # edges of distorted digits area
    epsilon = 0.001 * cv2.arcLength(contour, True)
    srcPoints = cv2.approxPolyDP(contour, epsilon, True)[:, 0]
    srcSqr = minSquare(srcPoints)

    # target horizontal digits area
    minRect = cv2.minAreaRect(contour)
    w, h = minRect[1]
    if w > h:
        deg = 0
    else:
        deg = 90
    dstRect = (minRect[0], minRect[1], deg)
    dstPoints = cv2.boxPoints(dstRect)
    dstBox = minSquare(dstPoints)

    # warp distorted area to horizontal rectangle
    src = np.array([srcSqr[0], srcSqr[1], srcSqr[2], srcSqr[3]], dtype="float32")
    dst = np.array([dstBox[0], dstBox[1], dstBox[2], dstBox[3]], dtype="float32")
    mat = cv2.getPerspectiveTransform(src, dst)

    h, w = img.shape
    warped = cv2.warpPerspective(img, mat, (w, h))

    # geometry of my 6+1 digit counter
    x1, y1 = dstBox[0]
    x2, y2 = dstBox[2]
    if x1 < 0:
        x1 = 0
    cell = y2 - y1
    
    #img[topY:bottomY+1, topX:bottomX+1]
    return warped[y1:y2, x2-3*cell-cell//2:x2+cell]


def similarity(a, b):
    return np.sum(np.where(a != b, 0, 1)) / a.size


def getSimilarity(digit, patterns):
    maxSimilarity = 0
    num = 0
    for p in patterns:
        s = similarity(digit, patterns[p])
        if s > maxSimilarity:
            maxSimilarity = s
            num = int(p[1])
    return (num, maxSimilarity)


def findDigits(img, blurr, low, ratio, patterns, boxes=None):
    """ find 7 digits in counter area
    return dictionary with digit position as key and 50x100 bw images as values """

    digitDict = {}
    digitImg = {}
    ch, cw = img.shape
    cw = int(cw // 7.7)  # width of one cell
    offset = 0
    minBright = 128

    for d in range(1, 8):
        if d == 7:
            offset = int(0.4 * cw)  # last cell has more space
        cell = img[0:ch, (d-1)*cw+offset:d*cw+offset]
        cell[cell < minBright] = 0
        if boxes is not None:
            boxCell = boxes[0:ch, (d-1)*cw+offset:d*cw+offset]
        edges = applyEdgeFilter(cell, blurr, low, ratio)
        # cv2.imwrite(f'cell_{d}.jpg', edges)
        h, w = cell.shape
        _, contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

        for cnt in contours:
            bx, by, bw, bh = cv2.boundingRect(cnt)
            box = np.array([[bx, by], [bx + bw, by], [bx + bw, by + bh], [bx, by + bh]])
            if bw / h > 0.11 and bw / h < 0.35 and bh / h > 0.38 and bh / h < 0.55:
                if not d in digitDict:
                    if 2 * bh > h:
                        bh = h // 2  # cap to max height of digits
                    # img[topY:bottomY+1, topX:bottomX+1]
                    dig = cv2.resize(cell[by:by+bh+1, bx:bx+bw+1], (50, 100), interpolation=cv2.INTER_AREA)
                    thres = minBright #  np.mean(dig)
                    digitImg[d] = cv2.threshold(dig, thres, 255, cv2.THRESH_BINARY)[1]
                    digit, maxSimilarity = getSimilarity(digitImg[d], patterns)
                    if maxSimilarity > minSimilarity:
                        digitDict[d] = digit
                        if boxes is not None:
                            cv2.drawContours(boxCell, [box], 0, (64, 255, 64), 2)  # valid box: green 
                    else:
                        if boxes is not None:
                            cv2.drawContours(boxCell, [box], 0, (196, 0, 0), 2)  # no digit in box: red 
                else:
                    if boxes is not None:
                        cv2.drawContours(boxCell, [box], 0, (128, 0, 196), 2)  # double box: violet
            else:
                if boxes is not None:
                    cv2.drawContours(boxCell, [box], 0, (0, 0, 255), 2)  # invalid box: blue

    return digitDict, digitImg


def numberFromDigits(digits):
    """ evaluate digit values and calculate number
    returns number or None if some digits are not recognized """

    num = 0

    if len(digits) != 7:
        missing = set(range(1, 8)) - set(digits.keys())
        eprint(datetime.now(), f"ERROR: incomplete digits {missing}")
        return None

    for d in sorted(digits):
        num = num * 10 + digits[d]

    return num


def readPatterns():
    return readDigits('digits.npz')


def getValue(digitPatterns):
    """ read digit patterns, then aquire image of 7 digit counter and compare with patterns
    return 0 and print detected number if successful, else return 1 """

    img = aquireGrayscaleImage("http://espcam1/snapshot.jpg")
    if img is None:
        return -3

    edges = applyEdgeFilter(img, area_blurr, area_low, area_ratio)
    contour = findLargestSquare(edges)

    if contour is None:
        eprint(datetime.now(), f"no contours on image")
        cv2.imwrite('image.jpg', img)
        cv2.imwrite('edges.jpg', edges)
        return -1

    counter = undoPerspectiveDistortion(img, contour)
    boxes = cv2.cvtColor(counter, cv2.COLOR_GRAY2BGR)

    # remove fine horizontal reflection lines
    width = 7
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (width, width))
    counter = cv2.morphologyEx(counter, cv2.MORPH_OPEN, kernel)

    digits, imgs = findDigits(counter, digit_blurr, digit_low, digit_ratio, digitPatterns, boxes=boxes)
    num = numberFromDigits(digits)

    if num is None:
        cv2.drawContours(img, [contour], 0, (255, 255, 255), 2)
        cv2.imwrite('image.jpg', img)
        cv2.imwrite('edges.jpg', edges)
        cv2.imwrite('counter.jpg', counter)
        boxes = cv2.cvtColor(boxes, cv2.COLOR_BGR2RGB)
        cv2.imwrite('boxes.jpg', boxes)
        for i in imgs:
            cv2.imwrite(f'digit_{i}.jpg', imgs[i])
        return -2

    return num


def validValue(num):
    global lastValue

    # failed reading or same reading
    if num < 0:
        return False
    
    # never validated before
    if lastValue == 0:
        print(datetime.now(), f"init {num/10:.1f} kW")
        lastValue = num - 1
        return False
    
    # reading went down or reading went up more than 1kWh
    if (num < lastValue) or (num > (lastValue + 10)):
        eprint(datetime.now(), f"suspicious {num/10:.1f} kW")
        return False
  
    lastValue = num
    return True 


def postValue(num):
    user_agent = 'Stromableser/1.0'
    headers = {'User-Agent': user_agent}
    url = 'http://localhost:8086/write?db=power&precision=s'
    post = f"energy,meter=main watt={num*100}"
    data = post.encode('utf-8')
    try:
        req = ul.request.Request(url, data, headers, method='POST')
        with ul.request.urlopen(req) as response:
            response.close()
            print(datetime.now(), f"sent {num/10:.1f} kW")
    except ul.error.URLError as e:
        eprint(datetime.now(), e.reason)
        return False
    
    return True


def main():
    print(datetime.now(), "Starting V1")
    digits = readPatterns()
    while True:
        num =  getValue(digits)
        if validValue(num):
            postValue(num)
        time.sleep(120)


if __name__ == '__main__':
    main()
