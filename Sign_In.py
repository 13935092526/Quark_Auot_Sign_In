import json
import math
import os
import re
import sys
import requests


# 获取环境变量
def get_env():
    webhook = os.environ.get('WebHook')

    if "COOKIE_QUARK" not in os.environ:
        error_msg = f"❌ 未添加COOKIE_QUARK变量"
        print(error_msg)
        if webhook:
            send_text(webhook,error_msg)
        sys.exit(0)

    cookie_list = re.split(r'\n|&&', os.environ.get('COOKIE_QUARK'))

    return cookie_list, webhook


# 企业微信机器人推送
def send_text(webhook, content, mentioned_list=None, mentioned_mobile_list=None):
    header = {
        "Content-Type": "application/json",
        "Charset": "UTF-8"
    }
    data = {

        "msgtype": "text",
        "text": {
            "content": content
            , "mentioned_list": mentioned_list
            , "mentioned_mobile_list": mentioned_mobile_list
        }
    }
    data = json.dumps(data)
    info = requests.post(url=webhook, data=data, headers=header)
    return info.content


# 封装自动签到的方法
class Quark:
    def __init__(self, user_data):
        """
        初始化方法
        :param user_data: 用户信息，用于后续的请求
        """
        self.param = user_data
        self.querystring = {
            "pr": "ucpro",
            "fr": "android",
            "kps": self.param.get('kps'),
            "sign": self.param.get('sign'),
            "vcode": self.param.get('vcode')
        }

    def convert_bytes(self, b):
        """
        将字节转换为 MB GB TB
        :param b: 字节数
        :return: 返回 MB GB TB
        """
        units = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
        # 获取容量单位
        # b<=0时赋值0
        # b>0 时计算log1024得出单位数并int整数化
        # 然后用min最小值函数，防止越界情况，如min（12,8）会取最大8
        unit_index = min(int(math.log(b, 1024)), len(units) - 1) if b > 0 else 0
        # 获取实际容量
        converted_value = b / (1024 ** unit_index)
        return f"{converted_value:.2f} {units[unit_index]}"

    def get_growth_info(self):
        """
        获取用户当前的签到信息
        :return: 返回字典，包含用户当前的签到信息
        """
        url = "https://drive-m.quark.cn/1/clouddrive/capacity/growth/info"
        response = requests.get(url=url, params=self.querystring).json()
        if response.get("data"):
            return response["data"]
        else:
            return False

    def get_growth_sign(self):
        """
        获取用户当前的签到信息
        :return: 返回字典，包含用户当前的签到信息
        """
        url = "https://drive-m.quark.cn/1/clouddrive/capacity/growth/sign"
        data = {"sign_cyclic": True}
        response = requests.post(url=url, json=data, params=self.querystring).json()
        if response.get("data"):
            return True, response["data"]["sign_daily_reward"]
        else:
            return False, response["message"]

    def queryBalance(self):
        """
        查询抽奖余额
        """
        url = "https://coral2.quark.cn/currency/v1/queryBalance"
        querystring = {
            "moduleCode": "1f3563d38896438db994f118d4ff53cb",
            "kps": self.param.get('kps'),
        }
        response = requests.get(url=url, params=querystring).json()
        # print(response)
        if response.get("data"):
            return response["data"]["balance"]
        else:
            return response["msg"]

    def do_sign(self):
        """
        执行签到任务
        :return: 返回一个字符串，包含签到结果
        """
        log = ""
        # 每日领空间
        growth_info = self.get_growth_info()
        if not growth_info:
            return f"❌ 签到异常: 获取成长信息失败\n"

        log += (
            f" {'88VIP' if growth_info['88VIP'] else '普通用户'} {self.param.get('user')}\n"
            f"💾 网盘总容量：{self.convert_bytes(growth_info['total_capacity'])}\n"
            f"签到总容量：")

        if "sign_reward" in growth_info['cap_composition']:
            log += f"{self.convert_bytes(growth_info['cap_composition']['sign_reward'])}\n"
        else:
            log += "0 MB\n"

        cap_sign = growth_info["cap_sign"]
        if cap_sign["sign_daily"]:
            log += (
                f"✅ 签到日志: \n今日已签到+{self.convert_bytes(cap_sign['sign_daily_reward'])}"
                f"\n连签进度({cap_sign['sign_progress']}/{cap_sign['sign_target']})\n"
            )
        else:
            sign, sign_return = self.get_growth_sign()
            if sign:
                log += (
                    f"✅ 执行签到: 今日签到+{self.convert_bytes(sign_return)}，"
                    f"连签进度({cap_sign['sign_progress'] + 1}/{cap_sign['sign_target']})\n"
                )
            else:
                log += f"❌ 签到异常: {sign_return}\n"

        return log


def main():
    """
    主函数
    :return: 返回一个字符串，包含签到结果
    """
    cookie_quark, webhook = get_env()
    msg = ""

    print("✅ 检测到共", len(cookie_quark), "个夸克账号\n")

    # 遍历用户
    for i, cookie in enumerate(cookie_quark):
        user_data = {}
        # 用户信息遍历
        for user_var in cookie.replace(' ', '').split(';'):
            if '=' in user_var:
                k, v = user_var.split('=')
                user_data[k] = v

        msg += f"🙍🏻‍♂️ 第{i + 1}个账号"
        # 登录
        msg += Quark(user_data).do_sign()

    if webhook:
        send_text(webhook,msg)
    return msg[:-1]


if __name__ == "__main__":
    print("----------夸克网盘开始签到----------")
    print(main())
    print("----------夸克网盘签到完毕----------")
