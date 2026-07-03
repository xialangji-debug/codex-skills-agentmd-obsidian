# fnOS Paths

## Login

- URL: `https://fnos.yuelaniot.com:5667`
- Use the saved Windows encrypted credential from `%USERPROFILE%\.codex\secrets\akq-firmware-release\fnos.credential.xml`.
- If login fails, ask the user to confirm the password before retrying.

## Domestic Release Tree

Navigate in 文件管理:

```text
团队文件
> 阿科奇
> 阿科奇-国内
> <product folder>
> <YYYYMMDD_HHMM>
```

Known top-level folders under `团队文件 > 阿科奇`:

- `阿科奇-国内`
- `阿科奇-海外`
- `资源文件`

Known examples under `阿科奇-国内`:

- `TW10_阿科奇_C10_光启象限`
- `TW10_阿科奇_C10_九学王乐智`
- `TW10_阿科奇_C10_小程序公版`
- `TW10-阿科奇-C10-河南旭五吉`
- `TW18_阿科奇_C10_定乾太阳树小程序`
- `TW18_阿科奇_JC2_儿童陪伴机_小程序公版`
- `TW18_阿科奇_JC8_九颗桃`
- `TW18_阿科奇_JC8_小程序儿童款公版`
- `TW18_阿科奇_JC8_熊顿小程序儿童款`
- `TW18_阿科奇_JC8_APP老人款公版`

If the local branch/product does not uniquely map to one folder, list matching TW10/TW18 candidates and ask the user. Do not create missing team, domestic, or product folders automatically.

## Release Folder

The release folder name is exactly the firmware release timestamp:

```text
YYYYMMDD_HHMM
```

Examples seen in the TW10 public app folder:

- `20260604_1008`
- `20260605_2208`
- `20260606_2100`
- `20260609_2100`
- `20260617_1500`
- `20260623_2100`
- `20260630_1830`
- `20260702_1400`

## Upload Behavior

When the user asks to release firmware, enter the matching timestamp folder and upload the files printed by `prepare_release_package.py`.

If the matching timestamp folder does not exist under the confirmed product folder, create only that final `YYYYMMDD_HHMM` folder automatically. Do not silently create a missing remote team, domestic, or product folder.

Upload normally includes:

- renamed firmware zip
- renamed `.mdb.txt`
- `readme.txt` only when the user provided it

Do not upload a Codex-generated readme summary. If a same-name remote file already exists, stop and ask before overwriting.
