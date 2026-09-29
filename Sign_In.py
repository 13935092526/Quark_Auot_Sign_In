import json
import math
import os
import re
import sys
import tempfile
from pathlib import Path

import requests

from t2i import render_template, push

GB = 1024 ** 3


# 获取环境变量
def get_env():
    webhook = os.environ.get('WebHook')

    if "COOKIE_QUARK" not in os.environ:
        error_msg = "⚠️ 未检测到COOKIE_QUARK变量"
        print(error_msg)
        if webhook:
            push([], title="夸克网盘 · 每日签到报告", text=error_msg, webhook=webhook, wecom_only=True)
        sys.exit(0)

    cookie_list = re.split(r'\n|&&', os.environ.get('COOKIE_QUARK'))

    return cookie_list, webhook


# 企业微信机器人推送（文字，作为图片渲染失败时的回退）
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


# 封装自动签到方法
class Quark:
    def __init__(self, user_data):
        """
        初始化签到
        :param user_data: 用户信息，用于后续的请求
        """
        self.param = user_data
        self.card = None  # 结构化签到数据，供图片模板渲染
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
        unit_index = min(int(math.log(b, 1024)), len(units) - 1) if b > 0 else 0
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
        查询金币余额
        """
        url = "https://coral2.quark.cn/currency/v1/queryBalance"
        querystring = {
            "moduleCode": "1f3563d38896438db994f118d4ff53cb",
            "kps": self.param.get('kps'),
        }
        response = requests.get(url=url, params=querystring).json()
        if response.get("data"):
            return response["data"]["balance"]
        else:
            return response["msg"]

    def _build_card(self, total_bytes, checkin_bytes, today_bytes, progress):
        """把签到数据整理成 quark_checkin 模板所需字段。"""
        total_cur = round(total_bytes / GB, 2)
        checkin_cur = min(round(checkin_bytes / GB, 2), total_cur)
        return {
            "phone": str(self.param.get('user') or ''),
            "total_cur": total_cur,
            "checkin_cur": checkin_cur,
            "today_gain": f"+{self.convert_bytes(today_bytes)}",
            "streak_done": max(0, min(int(progress), 7)),
        }

    def do_sign(self):
        """
        执行签到任务
        :return: 返回一个字符串，包含签到结果
        """
        log = ""
        # 每日空格
        growth_info = self.get_growth_info()
        if not growth_info:
            return f"❌ 签到异常: 获取成功信息失败\n"

        total_bytes = growth_info.get('total_capacity', 0)
        checkin_bytes = growth_info.get('cap_composition', {}).get('sign_reward', 0)
        cap_sign = growth_info.get("cap_sign", {})
        target = cap_sign.get('sign_target')

        log += (
            f" {'88VIP' if growth_info.get('88VIP') else '普通用户'} {self.param.get('user')}\n"
            f"📊 总可用容量：{self.convert_bytes(total_bytes)}\n"
            f"签到容量："
        )

        if "sign_reward" in growth_info.get('cap_composition', {}):
            log += f"{self.convert_bytes(checkin_bytes)}\n"
        else:
            log += "0 MB\n"

        today_bytes = 0
        progress = cap_sign.get('sign_progress', 0)
        if cap_sign.get("sign_daily"):
            today_bytes = cap_sign.get('sign_daily_reward', 0)
            log += (
                f"✅ 已签到 \n今日已签到+{self.convert_bytes(today_bytes)}"
                f"\n连续签到({progress}/{target})\n"
            )
        else:
            sign, sign_return = self.get_growth_sign()
            if sign:
                today_bytes = sign_return
                progress += 1
                log += (
                    f"✅ 签到成功: 今日已签到+{self.convert_bytes(today_bytes)}，"
                    f"连续签到({progress}/{target})\n"
                )
            else:
                log += f"❌ 签到异常: {sign_return}\n"

        # 记录结构化数据，供签到报告图片渲染
        self.card = self._build_card(total_bytes, checkin_bytes, today_bytes, progress)
        return log


def push_report(webhook, accounts, text_log):
    """优先推送签到报告图片；无数据或渲染失败时回退为文字推送。"""
    title = "夸克网盘 · 每日签到报告"
    if accounts:
        out = Path(tempfile.gettempdir()) / "quark_checkin.png"
        try:
            png = render_template("quark_checkin", {"accounts": accounts}, output=out)
            push([png], title=title, webhook=webhook, wecom_only=True)
            return
        except Exception as e:
            print(f"⚠️ 图片渲染/推送失败，回退文字推送: {e!r}")
    push([], title=title, text=text_log.strip(), webhook=webhook, wecom_only=True)


def main():
    """
    主函数
    :return: 返回一个字符串，包含签到结果
    """
    cookie_quark, webhook = get_env()
    msg = ""
    accounts = []

    print("🔍 检测到共", len(cookie_quark), "个账号\n")

    # 遍历用户
    for i, cookie in enumerate(cookie_quark):
        user_data = {}
        # 用户信息遍历
        for user_var in cookie.replace(' ', '').split(';'):
            if '=' in user_var:
                k, v = user_var.split('=')
                user_data[k] = v

        msg += f"📅『第{i + 1}个账号"
        # 签到
        quark = Quark(user_data)
        msg += quark.do_sign()
        if quark.card:
            accounts.append(quark.card)

    if webhook:
        push_report(webhook, accounts, msg)
    return msg[:-1]


if __name__ == "__main__":
    print("----------------开始执行签到----------------")
    print(main())
    print("----------------签到完成--------------")
