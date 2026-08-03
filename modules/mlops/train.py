"""
Multi-Horizon Multi-Task Training Pipeline for Module 4.
Trains dedicated Classification and Regression models for horizons t+1 through t+5.
"""

import logging
import sys

import mlflow
import mlflow.xgboost
import optuna
import pandas as pd
import xgboost as xgb
from sklearn.metrics import accuracy_score, root_mean_squared_error

from modules.mlops.config import config
from modules.mlops.dataset import create_targets, prepare_train_val_test_splits

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("mlops_train")

mlflow.set_tracking_uri(config.mlflow_tracking_uri)
mlflow.set_experiment(config.mlflow_experiment_name)


def optuna_optimize_cls(X_train, y_train, X_val, y_val, n_trials=5) -> dict:
    """Tunes XGBoost Classifier on validation accuracy."""

    def objective(trial: optuna.Trial) -> float:
        params = {
            "n_estimators": trial.suggest_int("n_estimators", 50, 150),
            "max_depth": trial.suggest_int("max_depth", 3, 7),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.1, log=True),
            "objective": "multi:softprob",
            "num_class": 3,
            "random_state": 42,
            "verbosity": 0,
        }
        model = xgb.XGBClassifier(**params)
        model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
        return accuracy_score(y_val, model.predict(X_val))

    study = optuna.create_study(direction="maximize")
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    study.optimize(objective, n_trials=n_trials)
    return study.best_params


def optuna_optimize_reg(X_train, y_train, X_val, y_val, n_trials=5) -> dict:
    """Tunes XGBoost Regressor on validation RMSE."""

    def objective(trial: optuna.Trial) -> float:
        params = {
            "n_estimators": trial.suggest_int("n_estimators", 50, 150),
            "max_depth": trial.suggest_int("max_depth", 3, 7),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.1, log=True),
            "random_state": 42,
            "verbosity": 0,
        }
        model = xgb.XGBRegressor(**params)
        model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
        return root_mean_squared_error(y_val, model.predict(X_val))

    study = optuna.create_study(direction="minimize")
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    study.optimize(objective, n_trials=n_trials)
    return study.best_params


def train_all_models() -> None:
    logger.info("Loading DVC-tracked dataset...")
    df = pd.read_parquet(config.parquet_path)

    logger.info(f"Generating targets for horizons: {config.target_horizons}...")
    df_targets = create_targets(df, horizons=config.target_horizons)

    for h in config.target_horizons:
        logger.info("=================================================")
        logger.info(f" 🚀 Training Models for Horizon t+{h} ")
        logger.info("=================================================")

        # --- 1. CLASSIFICATION (Trend Prediction) ---
        cls_target = f"target_class_t{h}"
        splits_cls = prepare_train_val_test_splits(df_targets, target_col=cls_target)

        best_cls_params = optuna_optimize_cls(
            splits_cls["X_train"],
            splits_cls["y_train"],
            splits_cls["X_val"],
            splits_cls["y_val"],
        )
        best_cls_params.update(
            {"objective": "multi:softprob", "num_class": 3, "random_state": 42}
        )

        with mlflow.start_run(run_name=f"XGB_Classifier_t{h}"):
            mlflow.set_tag("horizon", str(h))
            mlflow.set_tag("model_type", "classification")
            mlflow.log_params(best_cls_params)

            model_cls = xgb.XGBClassifier(**best_cls_params)
            model_cls.fit(splits_cls["X_train"], splits_cls["y_train"], verbose=False)

            val_acc = accuracy_score(
                splits_cls["y_val"], model_cls.predict(splits_cls["X_val"])
            )
            mlflow.log_metric("val_accuracy", val_acc)
            mlflow.xgboost.log_model(model_cls, name="model")
            logger.info(f"✅ [t+{h} Classification] Val Accuracy: {val_acc:.4f}")

        # --- 2. REGRESSION (Relative Return Prediction) ---
        reg_target = f"target_return_t{h}"
        splits_reg = prepare_train_val_test_splits(df_targets, target_col=reg_target)

        best_reg_params = optuna_optimize_reg(
            splits_reg["X_train"],
            splits_reg["y_train"],
            splits_reg["X_val"],
            splits_reg["y_val"],
        )
        best_reg_params.update({"random_state": 42})

        with mlflow.start_run(run_name=f"XGB_Regressor_t{h}"):
            mlflow.set_tag("horizon", str(h))
            mlflow.set_tag("model_type", "regression")
            mlflow.log_params(best_reg_params)

            model_reg = xgb.XGBRegressor(**best_reg_params)
            model_reg.fit(splits_reg["X_train"], splits_reg["y_train"], verbose=False)

            val_rmse = root_mean_squared_error(
                splits_reg["y_val"], model_reg.predict(splits_reg["X_val"])
            )
            mlflow.log_metric("val_rmse", val_rmse)
            mlflow.xgboost.log_model(model_reg, name="model")
            logger.info(f"✅ [t+{h} Regression] Val RMSE: {val_rmse:.5f}")


if __name__ == "__main__":
    train_all_models()