import argparse
import pathlib
import json

parser = argparse.ArgumentParser()
parser.add_argument("filename")


def create_data():
    return [{
        "series_name": "david_test_series",
        "series_help": "A series used to test the whole CI chain",
        "series_tags": {"tag_1": "spam", },
        "points": [
            {"value": 42.0,
             "tags": {
                 "tag_2": "eggs",
             },
             },
            {"value": 1234.0,
             "tags": {
                 "tag_2": "ham",
             },
             },
            {"value": 789.5,
             "tags": {
                 "tag_2": "foo",
             },
             },
        ],
    }]


def dump_results(results, filename):
    dump_file = pathlib.Path(filename)
    dump_file.write_text(json.dumps(results))


if __name__ == "__main__":
    args = parser.parse_args()
    dump_results(create_data(), args.filename)
