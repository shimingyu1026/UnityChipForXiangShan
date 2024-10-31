#coding=utf8
#***************************************************************************************
# This project is licensed under Mulan PSL v2.
# You can use this software according to the terms and conditions of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#          http://license.coscl.org.cn/MulanPSL2
#
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
#
# See the Mulan PSL v2 for more details.
#**************************************************************************************/
import os
import time
import base64
import re
import requests
from .logger import warning, debug
from .cfg import get_config


def merge_dict(dict1, dict2):
    """
    Merge two dictionaries
    """
    if not dict1:
        return dict2
    if not dict2:
        return dict1
    for key in dict2:
        if key in dict1:
            if isinstance(dict1[key], dict) and isinstance(dict2[key], dict):
                merge_dict(dict1[key], dict2[key])
            else:
                dict1[key] = dict2[key]
        else:
            dict1[key] = dict2[key]
    return dict1


def get_abs_path(path, sub, cfg):
    if path.startswith("/"):
        return os.path.join(path, sub)
    return os.path.abspath(os.path.join(
        os.path.dirname(cfg.__file__), path, sub))


def get_out_dir(subdir="", cfg=None):
    cfg = get_config(cfg)
    return get_abs_path(cfg.output.out_dir, subdir, cfg)


def get_rtl_dir(subdir="", cfg=None):
    cfg = get_config(cfg)
    return get_abs_path(cfg.rtl.cache_dir, subdir, cfg)


def time_format(seconds=None, fmt="%H-%M-%S"):
    """
    Convert seconds to time format
    """
    if seconds is None:
        seconds = time.time()
    return time.strftime(fmt, time.gmtime(seconds))


def base64_encode(input_str):
    input_bytes = input_str.encode('utf-8')
    base64_bytes = base64.b64encode(input_bytes)
    base64_str = base64_bytes.decode('utf-8')
    return base64_str


def base64_decode(base64_str):
    base64_bytes = base64_str.encode('utf-8')
    input_bytes = base64.b64decode(base64_bytes)
    return input_bytes.decode('utf-8')


def use_rtl(rtl_file, out_dir):
    rtl_path = os.path.join(out_dir, rtl_file)
    dir_name = os.path.basename(rtl_file).replace(".tar.gz", "")
    rtl_dir = os.path.join(out_dir, dir_name)
    if not os.path.exists(rtl_dir):
        debug("Extract %s to %s" % (rtl_path, out_dir))
        assert os.system(f"tar -xvf {rtl_path} -C {out_dir}")==0, "Extract RTL failed"
    lnk_file = os.path.join(out_dir, "rtl")
    if os.path.exists(lnk_file):
        debug("Remove old link %s" % lnk_file)
        os.remove(lnk_file)
    os.symlink(rtl_dir, lnk_file)


def download_rtl(base_url, out_dir, version="latest"):
    """
    Download RTL from url
    """
    debug("Download RTL from %s (%s)", base_url, version)
    if version != "latest":
        for f in os.listdir(out_dir):
            if version in f and "tar.gz" in f:
                debug("find %s in %s, ignore download" % (f, out_dir))
                use_rtl(f, out_dir)
                return True
        if version in base_url and ".tar.gz" in base_url:
            os.system(f"wget {base_url} -P {out_dir}")
        for f in os.listdir(out_dir):
            if version in f and "tar.gz" in f:
                debug("download %s success" % f)
                use_rtl(f, out_dir)
                return True
    if not base_url.endswith(".tar.gz"):
        resp = requests.get(base_url).content.decode('utf-8')
        all_urls = {}
        url = None
        for u in re.findall(r'http[s]?://\S+?\.tar\.gz', resp):
            all_urls[u.split("/")[-1].strip()] = u
            if version and version in u:
                url = u
                break
        if url is None:
            if version:
                warning(f"version {version} not found in {all_urls.keys()}, download the first one")
            assert len(all_urls) > 0, "No download url found (resp: %s)" % resp
            file_to_download = sorted(all_urls.keys())[0]
            for f in os.listdir(out_dir):
                if file_to_download in f and "tar.gz" in f:
                    debug("find %s in %s, ignore download", f, out_dir)
                    use_rtl(f, out_dir)
                    return True
            url = all_urls[file_to_download]
        debug(f"download {url} to {out_dir}")
        assert os.system(f"wget {url} -P {out_dir}") == 0, "Download RTL failed"
        use_rtl(url.split("/")[-1], out_dir)
    else:
        assert os.system(f"wget {base_url} -P {out_dir}") == 0, "Download RTL failed"
        use_rtl(base_url.split("/")[-1], out_dir)
    return True


def is_full_test():
    cfg = get_config()
    return cfg.test.test_model == "full_test"


def is_short_test():
    return not is_full_test()
