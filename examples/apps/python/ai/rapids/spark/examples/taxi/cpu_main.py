#
# Copyright (c) 2019, NVIDIA CORPORATION. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
from ai.rapids.spark.examples.taxi.consts import *
from ai.rapids.spark.examples.utility.args import parse_arguments
from ai.rapids.spark.examples.utility.utils import *
from ml.dmlc.xgboost4j.scala.spark import *
from pyspark.sql import SparkSession

def main(args, xgboost_args):
    spark = (SparkSession
        .builder
        .appName(args.mainClass)
        .getOrCreate())

    def prepare_data(path):
        reader = spark.read.format(args.format)
        if args.format == 'csv':
            reader.schema(schema).option('header', args.hasHeader)
        return vectorize(reader.load(path), label)

    if args.mode in [ 'all', 'train' ]:
        regressor = (XGBoostRegressor(**merge_dicts(default_params, xgboost_args))
            .setLabelCol(label)
            .setFeaturesCol('features'))

        if args.trainEvalDataPath:
            train_eval_data = prepare_data(args.trainEvalDataPath)
            regressor.setEvalSets({ 'test': train_eval_data })

        train_data = prepare_data(args.trainDataPath)
        model = with_benchmark('Training', lambda: regressor.fit(train_data))

        if args.modelPath:
            writer = model.write().overwrite() if args.overwrite else model
            writer.save(args.modelPath)
    else:
        model = XGBoostRegressionModel().load(args.modelPath)

    if args.mode in [ 'all', 'transform' ]:
        eval_data = prepare_data(args.evalDataPath)

        def transform():
            result = model.transform(eval_data).cache()
            result.foreachPartition(lambda _: None)
            return result

        result = with_benchmark('Transformation', transform)
        show_sample(args, result, label)
        with_benchmark('Evaluation', lambda: check_regression_accuracy(result, label))

    spark.stop()
