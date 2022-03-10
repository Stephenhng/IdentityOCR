import cv2
from matplotlib import pyplot as plt
import pytesseract
import numpy as np

modelFile = "model/res10_300x300_ssd_iter_140000.caffemodel"
configFile = "model/deploy.prototxt.txt"
FaceNet = cv2.dnn.readNetFromCaffe(configFile, modelFile)


def readBBoxCordinatesAndCenters(coordinates_txt):
    boxes = []
    centers = []
    with open(coordinates_txt,"r+") as file:
        for line in file:
            x1,y1, x2, y2, x3, y3, x4, y4 = np.int0(line.split(','))

            x = min(x1, x3)
            y = min(y1, y2)
            w = abs(min(x1,x3) - max(x2, x4))
            h = abs(min(y1,y2) - max(y3, y4))

            cX = round(int(x) + w/2.0)
            cY = round(int(y) + h/2.0)
            centers.append((cX, cY))
            bbox = (int(x), w, int(y), h)
            boxes.append(bbox)
    print("number of boxes", len(boxes))
    return np.array(boxes), np.array(centers)


def correctPerspective(img):
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    imgBlur = cv2.GaussianBlur(gray, (5,5), 1)
    imgCanny = cv2.Canny(imgBlur,10,100)
    #ret, thresh  = cv2.threshold(gray , 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    #thresh = cv2.adaptiveThreshold( gray,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY,11,2)
    
    kernel = np.ones((5,5), np.uint8)
    img_dilation = cv2.dilate( imgCanny, kernel, iterations=2)
    img_erosion = cv2.erode(img_dilation , kernel, iterations=1)

    cntrs ,hiarchy = cv2.findContours(img_erosion , cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    areas = [cv2.contourArea(c) for c in cntrs]
    max_index = np.argmax(areas)
    cnt = cntrs[max_index]
    x,y,w,h = cv2.boundingRect(cnt)

    #cv2.rectangle(img,(x,y),(x+w,y+h),(0,255,0),3)
    #c = max(cntrs, key = cv2.contourArea)
    #x,y,w,h = cv2.boundingRect(c)
    #cv2.rectangle(img,(x,y),(x+w,y+h),(255,0,0),5)
    
    rotrect = cv2.minAreaRect(cnt)
    box = cv2.boxPoints(rotrect)
    box = np.int0(box)
  
    angle = rotrect[-1]

    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    #print("Angle:", angle)
    (heigth_q, width_q) = img.shape[:2]
    (cx, cy) = (width_q // 2, heigth_q // 2)
    
    #rotated_img = rotate_bound(img, angle)
    #new_bbox = rotate_bbox(box, cx, cy,  heigth_q, width_q, angle)
    warped_img = warpImg(img, box,  width_q, heigth_q)
    
    plt.title("rotated image")
    plt.imshow(img)
    plt.show()

    
    plt.title("processed image")
    plt.imshow(img_erosion)
    plt.show()

    plt.title("warped image")
    plt.imshow(warped_img)
    plt.show()
    #cv2.imwrite("warped_img.jpg", warped_img)


    return warped_img

def reorder(myPoints):

    myPointsNew = np.zeros_like(myPoints)
    myPoints = myPoints.reshape((4,2))
    add = myPoints.sum(1)
    myPointsNew[0] = myPoints[np.argmin(add)]
    myPointsNew[3] = myPoints[np.argmax(add)]

    diff = np.diff(myPoints, axis = 1)
    
    myPointsNew[1] = myPoints[np.argmin(diff)]
    myPointsNew[2] = myPoints[np.argmax(diff)]

    return myPointsNew


def warpImg(img, points, w, h):

    points = reorder(points)
    pts1 = np.float32(points)
    pts2 = np.float32([[0,0], [w,0], [0,h], [w,h]])
    matrix =  cv2.getPerspectiveTransform(pts1, pts2)
    imgWarp = cv2.warpPerspective(img, matrix, (w,h))

    return imgWarp

def rotate_bound(image, angle):
    # grab the dimensions of the image and then determine the
    # centre
    (h, w) = image.shape[:2]
    (cX, cY) = (w // 2, h // 2)

    # grab the rotation matrix (applying the negative of the
    # angle to rotate clockwise), then grab the sine and cosine
    # (i.e., the rotation components of the matrix)
    M = cv2.getRotationMatrix2D((cX, cY), angle, 1.0)
    cos = np.abs(M[0, 0])
    sin = np.abs(M[0, 1])

    # compute the new bounding dimensions of the image
    nW = int((h * sin) + (w * cos))
    nH = int((h * cos) + (w * sin))

    # adjust the rotation matrix to take into account translation
    M[0, 2] += (nW / 2) - cX
    M[1, 2] += (nH / 2) - cY

    # perform the actual rotation and return the image
    return cv2.warpAffine(image, M, (nW, nH))

def rotate_bbox(bb, cx, cy, h, w, theta):
    
    new_bb = np.zeros_like(bb)
    for i,coord in enumerate(bb):
        # opencv calculates standard transformation matrix
        M = cv2.getRotationMatrix2D((cx, cy), theta, 1.0)
        # Grab  the rotation components of the matrix)
        cos = np.abs(M[0, 0])
        sin = np.abs(M[0, 1])
        # compute the new bounding dimensions of the image
        nW = int((h * sin) + (w * cos))
        nH = int((h * cos) + (w * sin))
        # adjust the rotation matrix to take into account translation
        M[0, 2] += (nW / 2) - cx
        M[1, 2] += (nH / 2) - cy
        # Prepare the vector to be transformed
        v = [coord[0],coord[1],1]
        # Perform the actual rotation and return the image
        calculated = np.dot(M,v)
        new_bb[i] = (calculated[0],calculated[1])
    
    return new_bb

def displayAllBoxes(img, rect):
    
    for rct in rect:
        x1, w, y1, h = rct
        cv2.rectangle(img, (x1, y1), (x1+w, y1+h), (255,0,0), 2)
        cX = round(int(x1) + w/2.0)
        cY = round(int(y1) + h/2.0)
        cv2.circle(img, (cX, cY), 7, (255, 0, 0), -1)
    
    return img

def getRightAndLeftBoxCenters(box_coordinates, box_indexes):
    
    right_centers = np.zeros((4,2), dtype=np.int32)
    left_centers = np.zeros((4,2), dtype=np.int32)
    
    right_centers_box_full = np.zeros((len(box_coordinates),2))
    left_centers_box_full  = np.zeros((len(box_coordinates),2))

    box1 = box_coordinates[box_indexes[0]]
    box2 = box_coordinates[box_indexes[1]]
    box3 = box_coordinates[box_indexes[2]]
    box4 = box_coordinates[box_indexes[3]]
 
    right_centers[0] = (box1[0]+ box1[1], round(box1[2]+box1[3]/2))
    right_centers[1] = (box2[0]+ box2[1], round(box2[2]+box2[3]/2))
    right_centers[2] = (box3[0]+ box3[1], round(box3[2]+box3[3]/2))
    right_centers[3] = (box4[0]+ box4[1], round(box4[2]+box4[3]/2))

    left_centers[0] =  (box1[0], round(box1[2]+box1[3]/2))
    left_centers[1] =  (box2[0], round(box2[2]+box2[3]/2))
    left_centers[2] =  (box3[0], round(box3[2]+box3[3]/2))
    left_centers[3] =  (box4[0], round(box4[2]+box4[3]/2))

    for i, box in enumerate(box_coordinates):
        right_centers_box_full[i] = (box[0]+ box[1], round(box[2]+box[3]/2))
        left_centers_box_full[i]  = (box[0], round(box[2]+ box[3]/2))
    
    return right_centers, left_centers, right_centers_box_full, left_centers_box_full


def drawlineBetweenBox(BoxNum, right_centers, left_centers_box_full, box2_r_neighbours, img):
    
    start_point = int(right_centers[BoxNum][0]),int(right_centers[BoxNum][1])
    box2_neighbour_indexes = np.squeeze(box2_r_neighbours)
    end_point = int(left_centers_box_full[box2_neighbour_indexes][0]), int(left_centers_box_full[box2_neighbour_indexes][1])

    return cv2.line(img, end_point,start_point,  (0,255,0), 3)

def denoiseImage(img):
    
    img_denoise = cv2.fastNlMeansDenoisingColored(img, None, 10, 10, 7, 15)
    imgGray = cv2.cvtColor(img_denoise , cv2.COLOR_BGR2GRAY)
    ret, imgf = cv2.threshold(imgGray , 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU) #imgf contains Binary image
    
    kernel = np.ones((3,3), np.uint8)
    img_dilation = cv2.dilate( imgf, kernel, iterations=1)
    img_erosion = cv2.erode(img_dilation , kernel, iterations=1)
    
    img_erosion = cv2.resize(img_erosion ,(img_erosion.shape[1], img_erosion.shape[0]))
    return img_erosion

def detectFace(img):

    h, w = img.shape[:2]
    blob = cv2.dnn.blobFromImage(cv2.resize(img, (300, 300)), 1.0,
    (300, 300), (104.0, 117.0, 123.0))
    FaceNet.setInput(blob)
    faces = FaceNet.forward()
    
    for i in range(faces.shape[2]):
        confidence = faces[0, 0, i, 2]
        if confidence > 0.6:
            print("Confidence:", confidence)
            return confidence
        return 0