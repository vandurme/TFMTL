# Copyright 2018 Johns Hopkins University. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =============================================================================


#!/usr/bin/env sh

# json format evaluation sets would be saved in data/pred/json

# 1A and 1B
# data to pred
mkdir -p data/pred/json/

# document level
cp /export/a05/mahsay/domain/data/json/doc -fr data/pred/json

# sentence level
cp /export/a05/mahsay/domain/data/json/sent -fr data/pred/json
