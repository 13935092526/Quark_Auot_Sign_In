# 夸克网盘自动签到

源代码来自于``BNDou`大佬的项目 https://github.com/BNDou/Auto_Check_In 中的夸克签到子功能，在此基础上进行部分重写

通过**GitHub Actions**每日自动执行，实现夸克网盘的自动签到，并实现企业微信机器人的推送服务

> 🆕 签到结果现以**杂志级信息卡片图片**推送到企业微信群（多账号堆叠为一张竖屏长图），图片由内置的 [`t2i`](t2i/) 渲染库离线生成；若图片渲染失败会自动回退为文字推送。



## 使用指南

1. ### 获取企业微信机器人

   1. 打开[企业微信](https://work.weixin.qq.com/)网页，注册一个企业

   2. 在【我的企业】中点击【微信插件】，用微信扫描二维码【邀请关注】，可直接在微信上接受到推送消息

   3. 注册成功后，登陆手机/桌面端企业微信，在企业群中点击设置，添加机器人，并获取**`WebHook`**码

      **注意：`WebHook`不要泄露给他人，否则可能会面临机器人推送轰炸**

3. ### 获取COOKIE_QUARK

   1. 使用手机抓包工具 [reqable](https://reqable.com/zh-CN/)，必须安装证书才能抓取。在安卓模拟器上安装该APP，并在模拟器设置中`磁盘共享`变为可写系统盘，通过MT管理器将证书移动至根目录指定位置。

   2. 搜索接口`https://drive-m.quark.cn/1/clouddrive/capacity/growth/info`获取请求信息

   3. 在URL中得到`kps`、`sign`、`vcode`三个参数，将其复制出来

      - 例如如获得以下链接：

        ```
        https://drive-m.quark.cn/1/clouddrive/capacity/growth/info?kps=AARWcp9UM71t5VzV9i5pBJ46666666666FFnr%2FHDAKlTnIb%2FAI8I0cWt%2B89iAR6%2BJfMwbXCP9vhae%2F2nwBeYEKnA%3D%3D ; sign=AATNT4rAQm1S3J156564648JTMfd5E0KLbsvSZ4sQfffz%2Be81U5OojkcIQ8%3D ; vcode=1741214159830
        ```

      - 将三个参数取出并整理得到以下形式，其中`user`需要自己命名

        ```
        user=111; kps=2222; sign=33333; vcode=444;
        ```

      - 支持同时签到多个账号，不同账号用**回车或 && 分隔**

        ```
        user=111; kps=2222; sign=33333; vcode=444;&&user=222; kps=3333; sign=444; vcode=5555;
        ```

        ```
        user=111; kps=2222; sign=33333; vcode=444;
        user=222; kps=3333; sign=44444; vcode=555;
        ```

4. ### Fork项目

   1. 将本项目 `Fork` 到自己的仓库
   2. 在自己**Fork项目**中，依次点击 **【Settings 】-> 【Secrets and variables】 -> 【Actions】**
   3. 在 **【Repository secrets】** 下点击 **【New Repository secrets】**
   4. **【Name】** 填写`COOKIE_QUARK`，**【Secret】** 填写上一步得到的COOKIE_QUARK信息
   5. 重复以上过程 **【Name】** 填写`WebHook`，**【Secret】** 填写WebHook码
      - 不填写WebHook不影响签到服务本体，只是没有签到推送服务

5. ### 测试

   1. 进入 **Actions** 选项卡，点击左侧的 **Quark** 
   2. 点击右侧的 **Run workflow** 按钮
   3. 在几秒钟后刷新网页，列表出现 左侧有绿灯的【**Quark** 】，点击进入
   4. 点击**【sign-in 】->【Run Sign-in】**查看日志
   5. 出现签到信息运行成功，企业微信群收到签到报告图片

## 关于 t2i 渲染库

`t2i/` 是从 [text2img](https://github.com/13935092526) 工具集内嵌进来的纯 Python 渲染库，`Sign_In.py` 通过 `from t2i import render_template, push` 调用：

- `render_template("quark_checkin", {"accounts": [...]}, output=...)` 渲染签到报告长图；
- `push([png], title=..., webhook=..., wecom_only=True)` 走企业微信 `image` 消息推送。

如需调整卡片样式，编辑 `t2i/templates/quark_checkin.py` 与共享主题 `t2i/templates/_style.py` 即可。
