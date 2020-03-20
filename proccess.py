import json
import pathlib
from work import words_clean

# preclean

with pathlib.Path("proccess.json").open("w") as file_out:
    datas = {}
    with pathlib.Path("results.json").open("r") as file_in:
        for key, values in json.load(file_in).items():
            for val in values:
                try:
                    words = list(words_clean(val))
                    if len(words) < 2:  # less 2，clean
                        continue
                except Exception as e:
                    print(e)
                    continue
                text = " ".join(words)
                if key not in datas:
                    datas[key] = set()
                datas[key].add(text)
            datas[key] = list(datas[key])
    file_out.write(json.dumps(datas, indent=4))
