codex-ccswitch-mobile 用于配置和排查“手机端 Codex 远程控制电脑端 Codex，
同时模型请求继续走电脑本机 CC Switch的站点（例如 icodeeasy 等自定义站点）
或其他本地 Responses API 代理”的场景。无需开通 codex  pro 会员。

开通条件包括：电脑端 Codex 可正常运行，手机端 ChatGPT升级到最新版，可以在菜单里看到 Codex ；
支持远程桌面会话，两端登录同一个 ChatGPT 账号，电脑端不是 API-key-only 登录，
本地代理正在运行，并且代理/上游支持 Codex 使用的 /v1/responses 协议。
验证成功的标准是手机端能控制电脑端 Codex！
本人是使用 mac 进行的测试，如是 Windows 请让 codex 稍作调整即可。
如有疑问可以联系我哦(123428316) ，感谢！

使用方法： 发给 codex 提示词：   安装这个skill  https://github.com/kuangre123/codex-ccswitch-mobile/   ，并实现手机端 Codex 远程控制电脑端 Codex

或者运行命令：
这行如有有可以跳过：  mkdir -p ~/.codex/skills

git clone https://github.com/kuangre123/codex-ccswitch-mobile.git ~/.codex/skills/codex-ccswitch-mobile

"codex-ccswitch-mobile" is used for configuring and troubleshooting the scenario where "the Codex on the mobile device remotely controls the Codex on the computer side,
while the model request continues to use the site of the computer's local CC Switch (such as icodeeasy and other custom sites) or other local Responses API proxies". There is no need to subscribe to the Codex Pro membership.
The activation conditions are as follows: The Codex on the computer end should be running normally, and the Codex on the mobile end needs to be updated to the latest version;
Support for remote desktop sessions, both ends log in with the same ChatGPT account, the computer end does not use API-key-only login,
The local proxy is running, and the proxy/upstream supports the /v1/responses protocol used by Codex.
The criterion for successful verification is that the mobile end can control the Codex on the computer end!
If you have any questions, please feel free to contact me (cb123428316@gmail.com).

Usage instructions: Send the Codex prompt message: Install this skill at https://github.com/kuangre123/codex-ccswitch-mobile/, and enable remote control of Codex on the mobile device from the computer.
