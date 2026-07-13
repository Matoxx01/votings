import os
import shutil

seed_dir = os.path.join(os.path.dirname(__file__), 'media_seed')
target_dir = os.path.join(os.path.dirname(__file__), 'media')

if os.path.exists(seed_dir):
    os.makedirs(target_dir, exist_ok=True)
    for item in os.listdir(seed_dir):
        s = os.path.join(seed_dir, item)
        d = os.path.join(target_dir, item)
        if os.path.isdir(s):
            shutil.copytree(s, d, dirs_exist_ok=True)
        else:
            if not os.path.exists(d):
                shutil.copy2(s, d)
