# from flask import Flask, render_template, request, redirect, url_for
# import configparser
# import subprocess
from flask import Flask, render_template, request, redirect, url_for
import configparser
import subprocess
import requests
import netifaces as ni

app = Flask(__name__)

def read_config(filename):
    config = configparser.ConfigParser()
    config.read(filename)
    return config

def save_config(filename, config):
    with open(filename, 'w') as configfile:
        config.write(configfile)

# def update_config(filename, section, public_ip, lan_ip):
#     config = configparser.ConfigParser()
#     config.read(filename)
#
#     # Kiểm tra xem section đã tồn tại trong config chưa
#     if not config.has_section(section):
#         config.add_section(section)
#
#     # Thêm hoặc cập nhật giá trị public_ip và lan_ip
#     config.set(section, 'public_ip', public_ip)
#     config.set(section, 'lan_ip', lan_ip)
#
#     # Lưu cấu hình mới vào file
#     with open(filename, 'w') as configfile:
#         config.write(configfile)

def update_config(filename, section, public_ip, lan_ip):
    config = configparser.ConfigParser()
    config.read(filename)

    # Kiểm tra xem section đã tồn tại trong config chưa
    if not config.has_section(section):
        config.add_section(section)

    # Thêm hoặc cập nhật giá trị public_ip và lan_ip
    if public_ip is not None:
        config.set(section, 'public_ip', public_ip)
    if lan_ip is not None:
        config.set(section, 'lan_ip', lan_ip)

    # Lưu cấu hình mới vào file
    with open(filename, 'w') as configfile:
        config.write(configfile)

def configure_pppoe(username, password, mac_address, interface, ip_address, port):
    # Thực hiện cấu hình PPPOE với địa chỉ MAC và thông tin đăng nhập được chỉ định
    pppoe_command = f"sudo pppoeconf -U {username} -P {password} -m {mac_address}"
    subprocess.run(pppoe_command, shell=True, check=True)

    # Thiết lập địa chỉ IP cho giao diện Ethernet
    ip_command = f"sudo ip addr add {ip_address} dev {interface}"
    subprocess.run(ip_command, shell=True, check=True)

    # Thiết lập chuyển tiếp cổng (port forwarding) từ giao diện Ethernet đến cổng mong muốn
    for protocol in ["tcp", "udp"]:
        for port_to_forward in ["80", "443", "1080", "1080"]:
            iptables_command = f"sudo iptables -t nat -A PREROUTING -i {interface} -p {protocol} --dport {port_to_forward} -j REDIRECT --to-port {port}"
            subprocess.run(iptables_command, shell=True, check=True)

def get_public_ip():
    try:
        response = requests.get('https://api.ipify.org?format=json')
        data = response.json()
        return data['ip']
    except Exception as e:
        print(f"Error occurred: {e}")
        return None

def get_lan_ip(interface):
    try:
        ni.ifaddresses(interface)
        ip = ni.ifaddresses(interface)[ni.AF_INET][0]['addr']
        return ip
    except Exception as e:
        print(f"Error occurred: {e}")
        return None

@app.route('/')
def index():
    # Hiển thị danh sách các cấu hình từ config.ini
    config = read_config('config.ini')
    return render_template('index.html', config=config)

@app.route('/hienthi')
def hienthi():
    # Hiển thị thông tin từ tệp config.ini
    config = read_config('config.ini')
    return render_template('hienthi.html', config=config)

@app.route('/configure', methods=['POST'])
def configure():
    # Xử lý yêu cầu cấu hình từ giao diện web
    username = request.form['username']
    password = request.form['password']
    mac_address = request.form['mac_address']
    interface = request.form['interface']
    ip_address = request.form['ip_address']
    port = request.form['port']
    # Lấy public_ip và lan_ip
    public_ip = get_public_ip()
    lan_ip = get_lan_ip(interface)

    # Cập nhật cấu hình trong config.ini
    update_config('config.ini', f'pppoe_{username}', public_ip, lan_ip)

    # Đọc cấu hình hiện tại
    config = read_config('config.ini')

    # Thêm hoặc cập nhật cấu hình mới
    section_name = f'pppoe_{username}'  # Tạo tên section dựa trên username
    if not config.has_section(section_name):
        config.add_section(section_name)
    config.set(section_name, 'username', username)
    config.set(section_name, 'password', password)
    config.set(section_name, 'mac_address', mac_address)
    config.set(section_name, 'interface', interface)
    config.set(section_name, 'ip_address', ip_address)
    config.set(section_name, 'port', port)

    # Lưu cấu hình mới vào file
    save_config('config.ini', config)

    # Cấu hình PPPOE
    configure_pppoe(username, password, mac_address, interface, ip_address, port)

    # Chuyển hướng người dùng về trang chủ
    return redirect(url_for('index'))

if __name__ == "__main__":
    app.run(debug=True)
