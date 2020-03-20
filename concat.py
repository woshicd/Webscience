import json
import pathlib

DATA_PATH = pathlib.Path("datas")
DATA_PATH.mkdir(exist_ok=True)
DATAS = {}

with pathlib.Path("results.json").open("w") as f_out:
    for item in DATA_PATH.glob("*.json"):
        with item.open("r") as f_in:
            try:
                for key, value in json.load(f_in).items():
                    if key not in DATAS:
                        DATAS[key] = value
                    else:
                        DATAS[key] = list(set(DATAS[key] + value))
            except Exception as e:
                print(item, e)
    f_out.write(json.dumps(DATAS, indent=4, ensure_ascii=False))


[print(k, len(v)) for k, v in DATAS.items()]
print(sum(map(len, DATAS.values())))
