"""ML pipeline — loads, transforms, trains, evaluates, deploys."""
import json
import os
import pickle
import shutil
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split


class Pipeline:
    """Orchestrates a configurable ML pipeline step by step."""

    # ── Initialisation ────────────────────────────────────────────────

    def __init__(self, config_path: str) -> None:
        with open(config_path) as f:
            cfg = json.load(f)
        self.data_path: str = cfg["data_path"]
        self.model_dir: str = cfg.get("model_dir", "./models")
        self.output_dir: str = cfg.get("output_dir", "./output")
        self.test_split: float = cfg.get("test_split", 0.2)
        self.random_seed: int = cfg.get("random_seed", 42)
        self.n_estimators: int = cfg.get("n_estimators", 100)
        self.max_depth: int | None = cfg.get("max_depth")
        self.features: list[str] = cfg.get("features", [])
        self.target: str = cfg["target"]
        self.deploy_target: str = cfg.get("deploy_target", "./deploy")

    # ── Pipeline steps ────────────────────────────────────────────────

    def _load(self) -> pd.DataFrame:
        return pd.read_csv(self.data_path)

    def _clean(self, df: pd.DataFrame) -> pd.DataFrame:
        """Drop nulls / duplicates, select features, one-hot encode."""
        df = df.dropna().drop_duplicates()
        if self.features:
            available = [c for c in self.features if c in df.columns]
            df = df[available + [self.target]]
        return pd.get_dummies(df, drop_first=True)

    def _split(self, df: pd.DataFrame):
        """Train / test split."""
        X = df.drop(columns=[self.target])
        y = df[self.target]
        return train_test_split(
            X, y, test_size=self.test_split, random_state=self.random_seed
        )

    def _train(self, X_train, y_train) -> RandomForestClassifier:
        model = RandomForestClassifier(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            random_state=self.random_seed,
        )
        model.fit(X_train, y_train)
        return model

    def _evaluate(self, model, X_test, y_test) -> dict[str, Any]:
        y_pred = model.predict(X_test)
        return {
            "accuracy": accuracy_score(y_test, y_pred),
            "report": classification_report(y_test, y_pred, output_dict=True),
        }

    def _save_model(self, model) -> str:
        Path(self.model_dir).mkdir(parents=True, exist_ok=True)
        path = os.path.join(self.model_dir, "model.pkl")
        with open(path, "wb") as f:
            pickle.dump(model, f)
        return path

    def _export_results(self, metrics: dict[str, Any]) -> str:
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        path = os.path.join(self.output_dir, "results.json")
        with open(path, "w") as f:
            json.dump(metrics, f, indent=2)
        return path

    def _deploy(self, model_path: str) -> str:
        deploy_dir = Path(self.deploy_target)
        if deploy_dir.exists():
            shutil.rmtree(str(deploy_dir))
        shutil.copytree(self.model_dir, str(deploy_dir))
        marker = deploy_dir / "deployed.txt"
        marker.write_text(
            f"Deployed at {__import__('datetime').datetime.now().isoformat()}"
        )
        return str(deploy_dir)

    # ── Public entry point ────────────────────────────────────────────

    def run(self) -> dict[str, Any]:
        """Execute the full pipeline end-to-end."""
        df = self._load()
        df = self._clean(df)
        X_train, X_test, y_train, y_test = self._split(df)
        model = self._train(X_train, y_train)
        metrics = self._evaluate(model, X_test, y_test)
        model_path = self._save_model(model)
        result_path = self._export_results(metrics)
        deploy_path = self._deploy(model_path)

        return {
            **metrics,
            "model_path": model_path,
            "result_path": result_path,
            "deploy_path": deploy_path,
        }
