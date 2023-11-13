from flask import Flask, render_template, Response,request,jsonify,redirect,url_for
import time
import cv2
from io import BytesIO
import flask
import requests
import traceback
import os
import torch
import numpy as np
import threading
from pathlib import Path
from PIL import Image
import xml.etree.ElementTree as ET
from urllib.parse import unquote#將中文URL編碼轉回中文

#model = torch.hub.load('yolov5', 'custom', path='yolov5/yolov5s.pt',source='local')

app = Flask(__name__)

menu_bar = f"""
         <nav class="sb-topnav navbar navbar-expand navbar-dark bg-dark">
            <!-- Navbar Brand-->
            <a class="navbar-brand ps-3" href="index">影像工具</a>
            <!-- Sidebar Toggle-->
            <button class="btn btn-link btn-sm order-1 order-lg-0 me-4 me-lg-0" onclick="ajaxRead()" id="sidebarToggle" href="#!">
                <span style="font-family:Comic Sans MS;font-size:14px;">
                    <div class="menu-icon"><i class="fas fa-bars"></i></div>
                </span>
            </button>

            <!-- Navbar Search-->
            <form class="d-none d-md-inline-block form-inline ms-auto me-0 me-md-3 my-2 my-md-0">


            </form>
            <!-- Navbar-->
            <ul class="navbar-nav ms-auto ms-md-0 me-3 me-lg-4">
                <li class="nav-item dropdown">
                    <a class="nav-link dropdown-toggle" id="navbarDropdown" href="#" role="button" data-bs-toggle="dropdown" aria-expanded="false"><i class="fas fa-user fa-fw"></i></a>
                    <ul class="dropdown-menu dropdown-menu-end" aria-labelledby="navbarDropdown">
                        <li><a class="dropdown-item" href="index">影像標註</a></li>
                        <li><hr class="dropdown-divider" /></li>
                        <li><a class="dropdown-item" href="logout">登出</a></li>
                    </ul>
                </li>
            </ul>
        </nav>
"""

@app.route('/', methods=['GET','POST'])
def index():
    global menu_bar
    root_path = f"static/uploads"
    if request.method == "POST":
        file_name = request.form['dataset']  # 前端表單name元素
        file_up = request.files.getlist("file[]")  # 前端表單name元素
        now = (time.strftime("%Y%m%d_%H%M%S"))
        # 找尋filepath目錄位置的照片
        save_path = f'{root_path}/{now}-{file_name}/images/'
        # 創建資料夾
        if not Path(save_path).exists():
            Path(save_path).mkdir(parents=True, exist_ok=True)
        #先建立類別txt檔
        with open(f'{root_path}/{now}-{file_name}/classes.txt', 'w') as f:
            f.write('')
        count_img = 0 #上傳圖片序列化
        for i in file_up:
            count_img += 1
            formats = i.filename[i.filename.index('.'):]
            fileName = str(count_img)
            if formats in ('.jpg', '.png', '.jpeg', '.HEIC', '.jfif'):
                formats = '.jpg'

                i.save(os.path.join(save_path, f"{fileName}{formats}"))
                try:
                    img = Image.open(os.path.join(save_path, f"{fileName}{formats}"))
                    img = exif_transpose(img)
                    img = img.convert("RGB")
                    dd = img.size
                    if 4000000 > dd[0] * dd[1] > 999000:
                        cropped = img.resize((int(dd[0] * 0.4), int(dd[1] * 0.4)))
                        cropped.save(os.path.join(save_path, f"{fileName}{formats}"))
                    elif dd[0] * dd[1] > 4000001:
                        cropped = img.resize((int(dd[0] * 0.2), int(dd[1] * 0.2)))
                        cropped.save(os.path.join(save_path, f"{fileName}{formats}"))
                except:
                    print(traceback.format_exc())
            elif formats == ".mp4":
                i.save(os.path.join(save_path, f"{fileName}{formats}"))
                cap = cv2.VideoCapture(os.path.join(save_path, f"{fileName}{formats}"))  # 替換為您的影片文件路徑
                frame_count = 0
                save_count = 0
                try:
                    while cap.isOpened():
                        print("第 ",frame_count,"幀")
                        frame_count += 1
                        ret, frame = cap.read()

                        if frame_count % 10 == 0:
                            print("存檔")
                            save_count += 1
                            dd = frame.shape[0:2]
                            print(dd[0]*dd[1])
                            if 4000000 > dd[0] * dd[1] > 999000:
                                print("存檔位置" ,os.path.join(save_path, f"{save_count}.jpg"))
                                img = cv2.resize(frame, (int(dd[0] * 0.4), int(dd[1] * 0.4)), interpolation=cv2.INTER_AREA)
                                cv2.imwrite(os.path.join(save_path, f"{save_count}.jpg"), img)
                            elif dd[0] * dd[1] > 4000001:
                                img = cv2.resize(frame, (int(dd[0] * 0.2), int(dd[1] * 0.2)), interpolation=cv2.INTER_AREA)
                                cv2.imwrite(os.path.join(save_path, f"{save_count}.jpg"), img)
                                print("存檔位置" ,os.path.join(save_path, f"{save_count}.jpg"))
                            else:
                                cv2.imwrite(os.path.join(save_path, f"{save_count}.jpg"), frame)
                                print("存檔位置", os.path.join(save_path, f"{save_count}.jpg"))
                except:
                    print("wrong")

                cap.release()
                os.remove(os.path.join(save_path, f"{fileName}{formats}"))

            dirs = []
            files = os.listdir(save_path)
            files.sort(key=lambda x: int(x[:-4]))
            for fi in files:
                dirs.append(f"{root_path}/{now}-{file_name}/images/{fi}".replace("\\", "/"))

            user_dirs = []
            for fidir in os.listdir(f'{root_path}'):

                user_dirs.append([fidir, fidir])
            print(dirs)
        return render_template('index.html', menu=menu_bar, dirs=dirs, urlguide=f"{now}-{file_name}",
                               obj_name=file_name, file_dir=user_dirs)
    else:
        name = request.args.get('filepath', '')
        print(name)
        if (name != ""):  # 若當前路徑有指定目錄名稱
            save_path = f'{root_path}/{name}/images/'
            dirs = []
            user_dirs = []
            try:
                files = os.listdir(save_path)
                files.sort(key=lambda x: int(x[:-4]))
                tags = []
                try:
                    with open(f'{root_path}/{name}/classes.txt', 'r') as f:
                        for text in f.read().split('\n'):
                            if text != "\n" and text != "":
                                tags.append(text)
                except:
                    with open(f'{root_path}/{name}/classes.txt', 'w') as f:
                        f.write('')

                for fi in files:
                    dirs.append(f"{root_path}/{name}/images/{fi}".replace("\\", "/"))

                sorted_folders = sorted(os.listdir(f'{root_path}'),
                                        key=extract_datetime, reverse=True)

                for fidir in sorted_folders:
                    # 分割檔案名稱並重新組裝後賦值到瀏覽器
                    y = fidir.split('-')[0].split('_')[0][0:4]
                    m = fidir.split('-')[0].split('_')[0][4:6]
                    d = fidir.split('-')[0].split('_')[0][6:8]
                    h = fidir.split('-')[0].split('_')[1][0:2]
                    min = fidir.split('-')[0].split('_')[1][2:4]
                    s = fidir.split('-')[0].split('_')[1][4:6]
                    user_dirs.append([fidir, f'{y}-{m}-{d} {h}:{min}:{s}'])
                print(dirs)
                return render_template('index.html', menu=menu_bar, dirs=dirs,tags=tags, obj_name = name.split('-')[1],dirslen= len(dirs), file_dir=user_dirs)
            except:
                print(traceback.format_exc())
        else:
            save_path = f'{root_path}/{name}/images/'
            dirs = []
            user_dirs = []

            sorted_folders = sorted(os.listdir(f'{root_path}'),
                                    key=extract_datetime, reverse=True)

            for fidir in sorted_folders:
                # 分割檔案名稱並重新組裝後賦值到瀏覽器
                y = fidir.split('-')[0].split('_')[0][0:4]
                m = fidir.split('-')[0].split('_')[0][4:6]
                d = fidir.split('-')[0].split('_')[0][6:8]
                h = fidir.split('-')[0].split('_')[1][0:2]
                min = fidir.split('-')[0].split('_')[1][2:4]
                s = fidir.split('-')[0].split('_')[1][4:6]
                user_dirs.append([fidir, f'{y}-{m}-{d} {h}:{min}:{s}'])
            print(dirs)
            return render_template('index.html', menu=menu_bar, dirs=dirs,dirslen=len(dirs), file_dir=user_dirs)

        return render_template('index.html',menu=menu_bar)

#紀錄標註類別
@app.route('/classname', methods=['POST'])
def classname():

    base_path =  os.getcwd()
    print(base_path)
    data = request.get_json()
    print(data)
    file_up = data["filepath"]

    tagname =  data["tags"]
    label_path = f"{file_up.split('/')[0]}/{file_up.split('/')[1]}/{file_up.split('/')[2]}/classes.txt"
    file_up = os.path.join(base_path, label_path).replace("\\", "/")
    try:
        with open(file_up, 'a') as f:
            f.write(f'{tagname}\n')

        data = {
            'data': 'finish',
        }
        return jsonify(data)
    except:
        data = {
            'data': 'fail',
        }
        return jsonify(data)

#儲存標註框資訊
@app.route('/list', methods=['POST'])
def labelsave():
    # 接收post
    data = request.get_json()
    file_path = data["filepath"]#資料夾路徑
    imgwidth = data["imgwidth"]#影像寬
    imgheight = data["imgheight"]#影像高
    ifpass = data["ifpass"]#判斷前端是否按下快捷鍵s做儲存
    label_list = data["label"]#標注資料陣列(內容 : 標注類別、xmin、ymin、xmax、ymax、長、寬)
    label_list_classname = data["labellist"]#圖片路徑

    print(file_path)
    print(imgwidth)
    print(imgheight)
    print(label_list_classname)
    print(label_list)

    labe_list_inPython = []
    coun_list = 0
    little_matrix = []

    # 處理所有label的標籤名、xmin,ymin,xmax,ymax,h,w
    for i in label_list:
        if coun_list < 6:
            little_matrix.append(i)
            coun_list += 1
        elif coun_list == 6:
            little_matrix.append(i)
            labe_list_inPython.append(little_matrix)
            little_matrix = []
            coun_list = 0
    print(labe_list_inPython)

    file_path_slash = file_path.replace("/", "\\")
    YOLO_Format = ""
    xml_content = f"""
            <annotation>
                <folder>{file_path.split('/')[3]}</folder>
                <filename>{file_path.split('/')[4]}</filename>
                <path>{file_path_slash}</path>
                <source>
                    <database>Unknown</database>
                </source>
                <size>
                    <width>{int(round(float(imgwidth), 1))}</width>
                    <height>{int(round(float(imgheight), 1))}</height>
                    <depth>3</depth>
                </size>
                <segmented>0</segmented>
            """
    print(labe_list_inPython)
    if labe_list_inPython != []:
        for labels in labe_list_inPython:
            xml_content += f"""<object>
                        <name>{labels[0]}</name>
                        <pose>Unspecified</pose>
                        <truncated>0</truncated>
                        <difficult>0</difficult>
                        <bndbox>
                            <xmin>{labels[1]}</xmin>
                            <ymin>{labels[2]}</ymin>
                            <xmax>{labels[3]}</xmax>
                            <ymax>{labels[4]}</ymax>
                        </bndbox>
                    </object>
                    """
        # for a in range(0,10):
        #     print("=" * a)
        # print(round(float(imgwidth),1),round(float(imgheight),1))
        print("標註數量: ", len(labe_list_inPython))
        print("標註Label: ", labels)
        # Yolo格式的開頭為對標註類別的對應序號
        for labels in labe_list_inPython:  # 依標註數量依序取出
            for li in range(len(label_list_classname)):  # 檢查標註類別的對應序號，若labels[0]序號與類別的排序對應則標為該類別序號
                if labels[0] == label_list_classname[li]:
                    ymin, xmin, ymax, xmax, image_w, image_h = [float(labels[2]), float(labels[1]), float(labels[4]),
                                                                float(labels[3]), int(round(float(imgwidth), 1)),
                                                                int(round(float(imgheight), 1))]
                    #中心點計算
                    #x = centerX / W
                    #y = centerY / H
                    (x_iw_ratio, y_ih_ratio) = (((xmin + xmax) * 0.5) / image_w, ((ymin + ymax) * 0.5) / image_h)
                    #寬高相對值
                    # w = boxWidth / W
                    # h = boxHeight / H
                    tw_iw_ratio = (xmax - xmin) * 1. / image_w
                    th_ih_ratio = (ymax - ymin) * 1. / image_h
                    YOLO_Format += f"""{li} {round(x_iw_ratio, 6)} {round(y_ih_ratio, 6)} {round(tw_iw_ratio, 6)} {round(th_ih_ratio, 6)}\n"""

    xml_content += "</annotation>"

    # print("XML : ")
    # print(xml_content)
    # print("YOLO Format : ")
    # print(YOLO_Format)
    save_path = f"static/uploads/{file_path.split('/')[2]}/labels/"
    save_path_xml = f"static/uploads/{file_path.split('/')[2]}/labels_xml/"
    print("" * 100)
    print(save_path)
    print(save_path_xml)
    print(ifpass)
    print("" * 100)

    # 創建資料夾
    if labe_list_inPython != []:  # 防止被寫入空值
        if not Path(save_path).exists():
            Path(save_path).mkdir(parents=True, exist_ok=True)
        if not Path(save_path_xml).exists():
            Path(save_path_xml).mkdir(parents=True, exist_ok=True)
        save_paths1 = os.path.join(save_path_xml, f"{file_path.split('/')[4].split('.')[0]}.xml").replace("\\", "/")
        print(save_paths1)
        with open(save_paths1, 'wt') as f:
            f.write(xml_content)
        save_paths2 = os.path.join(save_path, f"{file_path.split('/')[4].split('.')[0]}.txt").replace("\\", "/")
        with open(save_paths2, 'wt') as f:
            f.write(YOLO_Format)
    elif ifpass == "1":
        if not Path(save_path).exists():
            Path(save_path).mkdir(parents=True, exist_ok=True)
        if not Path(save_path_xml).exists():
            Path(save_path_xml).mkdir(parents=True, exist_ok=True)
        save_paths1 = os.path.join(save_path_xml, f"{file_path.split('/')[4].split('.')[0]}.xml").replace("\\", "/")
        print(save_paths1)
        with open(save_paths1, 'wt') as f:
            f.write(xml_content)
        save_paths2 = os.path.join(save_path, f"{file_path.split('/')[4].split('.')[0]}.txt").replace("\\", "/")
        with open(save_paths2, 'wt') as f:
            f.write(YOLO_Format)
    return jsonify("{result:OK}")

#讀取標註框資訊
@app.route('/read', methods=['POST'])
def readlabel():
    file_up = request.get_json()["filepath"]
    base_path = os.getcwd()
    label_path = f"{file_up.split('/')[0]}/{file_up.split('/')[1]}/{file_up.split('/')[2]}/labels_xml/{file_up.split('/')[4].split('.')[0]}.xml"
    file_up = os.path.join(base_path, label_path).replace("\\", "/")
    # tree = ET.parse(file_up)#中文路徑無法辨識
    print(file_up)
    try:
        with open(file_up, 'r', encoding='GBK') as file:
            tree = ET.parse(file)
        root = tree.getroot()
        print(file_up)

        lbl = []
        # 子節點與屬性
        for child in root:
            if (child.tag == "object"):
                # print(root.find("object").find("name").text)
                labn = child.find("name").text
                xmin = child.find("bndbox").find("xmin").text
                ymin = child.find("bndbox").find("ymin").text
                xmax = child.find("bndbox").find("xmax").text
                ymax = child.find("bndbox").find("ymax").text
                h = int(ymax) - int(ymin)
                w = int(xmax) - int(xmin)
                lbl.append([labn, xmin, ymin, xmax, ymax, h, w])

        # print(lbl)
        for lb in lbl:
            print(lb)
        data = {
            'data': lbl,
        }
    except:
        data = {
            'data': "",
        }
    return jsonify(data)
#快速標註
@app.route('/speedlabeling',methods=['POST'])
def speedlabel():
    data = request.get_json()
    filename = data["filename"]
    imgpath = f"static/uploads/{filename}/images/"
    modellist = []#模型列表
    bast_path = os.getcwd()
    checklabeled = 0#檢查是否有已標註資料

    # 點擊快速自動標註
    if data["mode"] == "select":
        for i in os.listdir(f"{bast_path}/static/models/".replace("\\", "/")):
            modellist.append(i)
        print(modellist)
        # 若當日模型訓練數量超過1個時，需排序
        print(sorted(modellist, key=len))
        print("{0}\static\{1}labels_xml".format(bast_path, imgpath[7:-7]))
        if Path(unquote("{0}\static\{1}labels_xml".format(bast_path, imgpath[7:-7]))).exists():
            print()
            for b in os.listdir(unquote("{0}\static\{1}labels_xml".format(bast_path, imgpath[7:-7]))):
                print(b)
                checklabeled = 1
        print(checklabeled)
        return jsonify({'status': modellist,'labeled':checklabeled})
    # 送出開始自動標註
    else:
        data = request.get_json()
        model = data['modelname']
        print("模型 ", model)
        checkpt = 0
        if model == "":
            return jsonify({'status': "no data"})
        try:
            for pt in os.listdir(f"{bast_path}/static/models/".replace("\\", "/")):
                if pt.split('.')[1] == "pt":
                    checkpt = 1  # 確認是否存在模型
            if checkpt == 0:
                return jsonify({'status': "no data"})
        except:
            return jsonify({'status': "no data"})
        print(f"調用模型 : {model}")
        model = torch.hub.load('yolov5', 'custom',
                               path=f'static/models/{model}',
                               source='local')
        label_class = {}  # 存放類別的classes.txt
        for img in os.listdir(imgpath):  # 遍歷每一張圖片
            frame = cv2.imread(f'{imgpath}/{img}')
            YOLO_Format = ""
            xml_content = f"""
                              <annotation>
                                  <folder>images</folder>
                                  <filename>{img}</filename>
                                  <path>{imgpath}{img}</path>
                                  <source>
                                      <database>Unknown</database>
                                  </source>
                                  <size>
                                      <width>{frame.shape[1]}</width>
                                      <height>{frame.shape[0]}</height>
                                      <depth>3</depth>
                                  </size>
                                  <segmented>0</segmented>
                              """
            start = time.time()
            results = model(frame)
            if len(results.pandas().xyxy[0]) > 0:
                for resultI in range(len(results.pandas().xyxy[0])):
                    x = int(results.pandas().xyxy[0]["xmin"][resultI])
                    y = int(results.pandas().xyxy[0]["ymin"][resultI])
                    w = int(results.pandas().xyxy[0]["xmax"][resultI])
                    h = int(results.pandas().xyxy[0]["ymax"][resultI])
                    confi = int(results.pandas().xyxy[0]["confidence"][resultI] * 100)
                    names_label = results.pandas().xyxy[0]["name"][resultI]
                    label_class[results.pandas().xyxy[0]["class"][resultI]] = names_label

                    if confi > 10:
                        # cv2.rectangle(frame, (x, y), (w, h), (0, 255, 0), 5)
                        # font = cv2.FONT_HERSHEY_COMPLEX
                        # cv2.putText(frame, f'{names_label}_{confi}%', (x + 10, y + 10), font, 1, (255, 255, 255), 1,
                        #             cv2.LINE_AA)
                        # cv2.putText(frame, f'X : {int((w + x) / 2)},Y:{int((y + h) / 2)}',
                        #             (int((w + x) / 2) + 10, int((y + h) / 2) + 10), font, 1, (255, 255, 255), 1,
                        #             cv2.LINE_AA)
                        xml_content += f"""<object>
                                                <name>{names_label}</name>
                                                <pose>Unspecified</pose>
                                                <truncated>0</truncated>
                                                <difficult>0</difficult>
                                                <bndbox>
                                                    <xmin>{x}</xmin>
                                                    <ymin>{y}</ymin>
                                                    <xmax>{w}</xmax>
                                                    <ymax>{h}</ymax>
                                                </bndbox>
                                            </object>
                                        """
                        ymin, xmin, ymax, xmax, image_w, image_h = [y, x,
                                                                    h, w,
                                                                    frame.shape[1],
                                                                    frame.shape[0]]
                        (x_iw_ratio, y_ih_ratio) = (
                            ((xmin + xmax) * 0.5) / image_w, ((ymin + ymax) * 0.5) / image_h)
                        tw_iw_ratio = (xmax - xmin) * 1. / image_w
                        th_ih_ratio = (ymax - ymin) * 1. / image_h
                        YOLO_Format += f"""{results.pandas().xyxy[0]["class"][resultI]} {round(x_iw_ratio, 6)} {round(y_ih_ratio, 6)} {round(tw_iw_ratio, 6)} {round(th_ih_ratio, 6)}\n"""

                xml_content += "</annotation>"
                save_path = f"{bast_path}/{imgpath[0:-7]}labels/".replace('\\', '/')
                save_path_xml = f"{bast_path}/{imgpath[0:-7]}labels_xml/".replace('\\', '/')

                print(save_path)
                print(save_path_xml)
                if not Path(save_path).exists():
                    Path(save_path).mkdir(parents=True, exist_ok=True)
                if not Path(save_path_xml).exists():
                    Path(save_path_xml).mkdir(parents=True, exist_ok=True)

                save_paths1 = os.path.join(save_path_xml, f"{img.split('.')[0]}.xml").replace("\\", "/")
                # print(save_paths1)
                with open(save_paths1, 'wt') as f:
                    f.write(xml_content)
                #
                save_paths2 = os.path.join(save_path, f"{img.split('.')[0]}.txt").replace("\\", "/")
                # print(save_paths2)
                with open(save_paths2, 'wt') as f:
                    f.write(YOLO_Format)  # return HttpResponse(f'{file_path}')
                classfile = os.path.join(save_path[:-7], f"classes.txt").replace("\\", "/")
                classtexts = ""
                for cls in range(len(label_class)):
                    # print(sorted(label_class.items())[cls][1])#列出標註物的排序
                    classtexts += f"{sorted(label_class.items())[cls][1]}\n"
                with open(classfile, 'wt') as f:
                    f.write(classtexts)
            else:
                print("NO Labeling")

            # print("第",img,"張圖片 ================================================")
            # print(YOLO_Format)
            # print(xml_content)
            # print(label_class)
        return jsonify({'status': "成功"})

#資料夾排序
def extract_datetime(folder_name):
    # 設定資料夾名稱的格式為 'YYYYMMDD_HHMMSS'
    # 例如 '20230723_150202'
    print(folder_name.split('-')[0].split('_'))
    date_str, time_str = folder_name.split('-')[0].split('_')
    year = int(date_str[:4])
    month = int(date_str[4:6])
    day = int(date_str[6:8])
    hour = int(time_str[:2])
    minute = int(time_str[2:4])
    second = int(time_str[4:6])
    return (year, month, day, hour, minute, second)

#依據相片EXIF資訊修正方位
def exif_transpose(img):
    if not img:
        return img

    exif_orientation_tag = 274

    # Check for EXIF data (only present on some files)
    if hasattr(img, "_getexif") and isinstance(img._getexif(),
                                               dict) and exif_orientation_tag in img._getexif():
        exif_data = img._getexif()
        orientation = exif_data[exif_orientation_tag]

        # Handle EXIF Orientation
        if orientation == 1:
            # Normal image - nothing to do!
            pass
        elif orientation == 2:
            # Mirrored left to right
            img = img.transpose(Image.FLIP_LEFT_RIGHT)
        elif orientation == 3:
            # Rotated 180 degrees
            img = img.rotate(180)
        elif orientation == 4:
            # Mirrored top to bottom
            img = img.rotate(180).transpose(Image.FLIP_LEFT_RIGHT)
        elif orientation == 5:
            # Mirrored along top-left diagonal
            img = img.rotate(-90, expand=True).transpose(Image.FLIP_LEFT_RIGHT)
        elif orientation == 6:
            # Rotated 90 degrees
            img = img.rotate(-90, expand=True)
        elif orientation == 7:
            # Mirrored along top-right diagonal
            img = img.rotate(90, expand=True).transpose(Image.FLIP_LEFT_RIGHT)
        elif orientation == 8:
            # Rotated 270 degrees
            img = img.rotate(90, expand=True)

    return img


if __name__ == '__main__':

    app.run(host='0.0.0.0',debug=True,threaded=True)
