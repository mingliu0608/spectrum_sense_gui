import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QTextEdit, QPushButton, QLineEdit, QLabel,QHBoxLayout,QComboBox,QGridLayout
from PyQt5.QtCore import Qt
import socket
import struct
import numpy as np
import queue
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5 import QtCore, QtGui, QtWidgets
from util import send_scanning_spectrum_msg,read_second_byte,get_ip,get_time
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont
from threading import Event
import pyqtgraph as pg
from plotWidget import CrosshairPlotWidget
start_rec_event = Event()  # 默认False
class DataReceiver(QThread):
    dataReceived = pyqtSignal(list)
    msg_printer =  pyqtSignal(str)
    end_signal = pyqtSignal(int)
    def __init__(self,socket):
        super().__init__()
        # self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # self.s.bind(("192.168.201.110",9999))
        self.s = self.set_socket(socket)
        self.ctn = 0 
    def set_socket(self,so):
        self.s = so
    def get_socket(self):
        return self.s
    def set_ctn(self,ctn):
        self.ctn = ctn
    def get_ctn(self):
        return self.ctn
    def so_change_signal_handler(self):
        pass
    def run(self):
    
        while True:
            start_rec_event.wait()
            try:
                s= self.get_socket()
               # 接收数据:
                # if(ctn >=start_freq+band_width):
                #     break
                # if(start_freq+band_width - ctn <= size):
                # print(self.s.getsockname())
                data, addr = s.recvfrom(1024)
                if(data == b'\x0c\x11\x11\x11\x11\x0c'):
                    self.msg_printer.emit(f"建立连接，主控地址为： {addr}")
                elif(data == b'\x0c\x00\x00\x00\x00\x0c'):
                    self.msg_printer.emit(f"主控异常，主控地址为： {addr}")
                else:
                    size = read_second_byte(data)
                    self.set_ctn(size + self.get_ctn())
                    format = struct.Struct(
                    '>' + 'b' + 'b' + size* 'Hf' + 'b')  # 1字节起始字节 + 1字节命令字段 + 2字节unsigned short序号+ 4字节 float功率值+1字节结束字节
                    (begin_flag,freq_dot_num,*_data,end_flag)= format.unpack_from(data)
                    self.msg_printer.emit(f"Received from {addr}")
                    self.dataReceived.emit(_data)
                    #以太网最大分组长度为1500，ip20,udp8，最大1472，设定1024最大/packet
                    print("receving from" + str(addr))  
        
                self.end_signal.emit(self.get_ctn())
            except socket.error:
                pass

class UDPReceiver(QMainWindow):
    so_change_signal = pyqtSignal(int)
    def __init__(self):
        super().__init__()
        self.device_addr = ("192.168.201.253",9999)
        self.initUI()
        # self.initSocket()
        self.receiver_thread = DataReceiver(self.get_socket())
        self.receiver_thread.msg_printer.connect(self.updateText)
        self.receiver_thread.end_signal.connect(self.hendle_end_signal)
        self.receiver_thread.dataReceived.connect(self.update_data)
        self.receiver_thread.start()
        self.plot_freq = []
        self.plot_power = []
    def initUI(self):
        self.setWindowTitle('频谱感知调试程序by闸北陆小洪')
        self.setGeometry(200, 200, 600, 800)
        
        layout = QVBoxLayout()

        layout_plot = QGridLayout()
        
    
        text_monitor_layer=  QHBoxLayout()

        input_layout = QHBoxLayout()
        self.data_edit = QTextEdit()
        self.data_edit.setReadOnly(True)
        # self.data_edit.setMaximumHeight(500)
        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        # self.log_edit.setMaximumHeight(500)
        # self.text_edit.setFixedHeight(200)
        text_monitor_layer.addWidget(self.data_edit)
        text_monitor_layer.addWidget(self.log_edit)

        self.plot_widget = CrosshairPlotWidget()
        # self.plot_widget.setMinimumHeight(800)
        layout_plot.addWidget(self.plot_widget)
        # layout_plot.setContentsMargins(20,100,20,100)

        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)
        self.addr_label = QLabel("本地主机地址")
        input_layout.addWidget(self.addr_label)
        self.addr_combobox = QComboBox()
        self.addr_combobox.setEditable(True)
        # self.combobox.view().setSelectionMode(QComboBox.mu)
        self.addr_combobox.addItems(get_ip())
        self.addr_combobox.setCurrentIndex(2)
        # self.addr_combobox.currentIndexChanged.connect(self.addr_change_handler)
        input_layout.addWidget(self.addr_combobox)

        #本地监听端口控件
        self.port_label = QLabel("端口")    
        input_layout.addWidget(self.port_label)
        self.port_input = QLineEdit()
        self.port_input.setText('9999')
        input_layout.addWidget(self.port_input)


              
        #主控地址控件
        self.master_aadr_label = QLabel("主控地址")    
        input_layout.addWidget(self.master_aadr_label)
        self.master_aadr = QLineEdit()
        self.master_aadr.setText('192.168.201.253')
        input_layout.addWidget(self.master_aadr)


        #主控端口控件

        self.master_port_label = QLabel("主控端口")    
        input_layout.addWidget(self.master_port_label)
        self.master_port_input = QLineEdit()
        self.master_port_input.setText('9999')
        input_layout.addWidget(self.master_port_input)

        #打开本地端口监听按钮

        self.udp_connect_btn = QPushButton("打开")
        self.udp_connect_btn.clicked.connect(self.initSocket)
        input_layout.addWidget(self.udp_connect_btn)

        self.connect_check_btn = QPushButton("连通性检测")
        self.connect_check_btn.clicked.connect(self.connect_check)
        self.connect_check_btn.setDisabled(True)
        input_layout.addWidget(self.connect_check_btn)
        #扫频
        self.freq_start_label = QLabel("起始频率")
        input_layout.addWidget(self.freq_start_label)
        self.freq_start_input = QLineEdit()
        self.freq_start_input.setText('300')
        input_layout.addWidget(self.freq_start_input)

        self.freq_end_label = QLabel("终止频率")    
        input_layout.addWidget(self.freq_end_label)
        self.freq_end_input = QLineEdit()
        self.freq_end_input.setText('1300')
        input_layout.addWidget(self.freq_end_input)
        
        self.send_button = QPushButton("发送扫频指令")
        self.send_button.clicked.connect(self.sendData)
        self.send_button.setDisabled(True)
        input_layout.addWidget(self.send_button)


        layout.addLayout(layout_plot)
        layout.addLayout(text_monitor_layer)   
        layout.addLayout(input_layout)    
        # central_widget = QWidget()
        # central_widget.setLayout(layout)
        # self.setCentralWidget(central_widget)


        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    def connect_check(self):
        try:
            self.udp_socket.sendto(b'\x0c\xff\xff\xff\xff\x0c',(self.master_aadr.text(),int(self.master_port_input.text())))
            self.logger_write("正在请求上位机，连通性测试中......")
        except Exception as e:
            self.logger_write(str(e))
    def updateText(self, data):
        self.logger_write(data)
    def get_freq_range(self):
        return  int(self.freq_start_input.text()), int(self.freq_end_input.text())
    def hendle_end_signal(self,ctn):
        freq_bandwidth = self.get_freq_range()[1] - self.get_freq_range()[0]
        max_x,max_y = self.plot_widget.updatePlot(self.plot_freq,self.plot_power)

        if(ctn>=freq_bandwidth):
            #清空数据
            # self.send_button.setDisabled(True)
            self.logger_write("max freq value:"+str(max_y)+" db at "+str(max_x)+" MHz")
            self.plot_freq = []
            self.plot_power = []
            self.receiver_thread.set_ctn(0)
            # self.plot_widget.clearPlot()
    def sendData(self):
        # self.initSocket((self.addr_combobox.currentText(),9999))
        try:
            (start_freq,end_freq) = self.get_freq_range()
            send_scanning_spectrum_msg((self.master_aadr.text(),int(self.master_port_input.text())), start_freq,end_freq)
            self.logger_write("发送扫频指令，扫频频率范围为%d MHz ~ %d MHz"%(start_freq,end_freq))
            # self.send_button.setDisabled(True)
            self.plot_widget.set_range(start_freq,end_freq)
        except Exception as e:  
            self.logger_write("Error: Invalid input" +str(e))

    def initSocket(self):
        start_rec_event.clear()
        try:
            if self.udp_socket:
                self.udp_socket.close()
            # 更改绑定的本地IP地址和端口
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_socket.bind((self.addr_combobox.currentText(),int(self.port_input.text())))
            self.logger_write("UDP套接字绑定到 {}:{} 成功".format(self.addr_combobox.currentText(), int(self.port_input.text())))
            self.receiver_thread.set_socket(self.udp_socket)
            self.connect_check_btn.setDisabled(False)
            self.send_button.setDisabled(False)
            start_rec_event.set()
        except Exception as e:
            self.logger_write("UDP套接字绑定失败:"+str( e))
            
            # self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        #self.udp_socket.setblocking(False)  # 将 socket 设置为非阻塞模式
    def get_socket(self):
        return self.udp_socket
    def update_data(self,data_list):     
   
        self.data_edit.append(str(data_list))
        _freq = [data_list[i] for i in range(len(data_list)) if i % 2 == 0]
        _power = [data_list[i] for i in range(len(data_list)) if i % 2 != 0]
        self.plot_freq = [*self.plot_freq,*_freq] 
        self.plot_power = [*self.plot_power,*_power]

    def logger_write(self,msg):
        self.log_edit.append("["+get_time()+"] "+msg)
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()

    def closeEvent(self, event):
        self.udp_socket.close()
        event.accept()



if __name__ == '__main__':
    app = QApplication(sys.argv)
        # 设置全局字体大小为12
    font = QFont("Arial", 12)
    app.setFont(font)
    receiver = UDPReceiver()
    receiver.show()
    
    #timer = app.createTimer(receiver.receiveData, 100)  # 100ms 定时器，用于周期性检查是否有数据到达
    
    sys.exit(app.exec_())
