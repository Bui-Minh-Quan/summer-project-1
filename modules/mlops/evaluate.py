"""
Evaluation and Quality Gate Pipeline for Multi-Horizon Models.
Evaluates Classification & Regression candidates on the 2026 Test set.
"""

import logging
import sys

import mlflow
import pandas as pd
from mlflow.tracking import MlflowClient
from sklearn.metrics import accuracy_score, root_mean_squared_error

from modules.mlops.config import config
from modules.mlops.dataset import create_targets, prepare_train_val_test_splits

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("mlops_evaluate")

mlflow.set_tracking_uri(config.mlflow_tracking_uri)
client = MlflowClient()


def evaluate_and_promote_all() -> None:
    df = pd.read_parquet(config.parquet_path)
    df_targets = create_targets(df, horizons=config.target_horizons)

    experiment = client.get_experiment_by_name(config.mlflow_experiment_name)
    if not experiment:
        logger.error("No experiment found in MLflow!")
        return

    for h in config.target_horizons:
        logger.info("------------------------------------------------")
        logger.info(f" 🔎 Evaluating Candidates for Horizon t+{h} ")
        logger.info("------------------------------------------------")

        # --- 1. Evaluate Classification Candidate ---
        cls_target = f"target_class_t{h}"
        splits_cls = prepare_train_val_test_splits(df_targets, target_col=cls_target)

        cls_runs = client.search_runs(
            experiment_ids=[experiment.experiment_id],
            filter_string=f"tags.horizon = '{h}' AND tags.model_type = 'classification'",
            order_by=["start_time DESC"],
            max_results=1,
        )

        if cls_runs:
            run_id = cls_runs[0].info.run_id
            cls_model = mlflow.xgboost.load_model(f"runs:/{run_id}/model")
            test_acc = accuracy_score(
                splits_cls["y_test"], cls_model.predict(splits_cls["X_test"])
            )

            logger.info(f"[t+{h} Classification] Test Accuracy: {test_acc:.4f} (Gate: >= {config.min_accuracy})")

            if test_acc >= config.min_accuracy:
                model_name = f"VN30_Trend_Classifier_t{h}"
                ver = mlflow.register_model(f"runs:/{run_id}/model", name=model_name)
                client.set_registered_model_alias(name=model_name, alias="production", version=ver.version)
                logger.info(f"🎉 Promoted {model_name} (v{ver.version}) to @production")
            else:
                logger.warning(f"❌ Rejected {cls_target}: Test accuracy below gate.")

        # --- 2. Evaluate Regression Candidate ---
        reg_target = f"target_return_t{h}"
        splits_reg = prepare_train_val_test_splits(df_targets, target_col=reg_target)

        reg_runs = client.search_runs(
            experiment_ids=[experiment.experiment_id],
            filter_string=f"tags.horizon = '{h}' AND tags.model_type = 'regression'",
            order_by=["start_time DESC"],
            max_results=1,
        )

        if reg_runs:
            run_id = reg_runs[0].info.run_id
            reg_model = mlflow.xgboost.load_model(f"runs:/{run_id}/model")
            test_rmse = root_mean_squared_error(
                splits_reg["y_test"], reg_model.predict(splits_reg["X_test"])
            )

            logger.info(f"[t+{h} Regression] Test RMSE: {test_rmse:.5f} (Gate: <= {config.max_rmse})")

            if test_rmse <= config.max_rmse:
                model_name = f"VN30_Return_Regressor_t{h}"
                ver = mlflow.register_model(f"runs:/{run_id}/model", name=model_name)
                client.set_registered_model_alias(name=model_name, alias="production", version=ver.version)
                logger.info(f"🎉 Promoted {model_name} (v{ver.version}) to @production")
            else:
                logger.warning(f"❌ Rejected {reg_target}: Test RMSE above gate.")


if __name__ == "__main__":
    evaluate_and_promote_all()