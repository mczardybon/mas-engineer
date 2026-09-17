"""ML pipeline — loads, transforms, trains, evaluates, deploys."""
import json
import os
import pickle
import shutil
from pathlib import Path
from typing import Any


class Pipeline:
    """Monolithic pipeline doing everything."""

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

    def run(self) -> dict[str, Any]:
        """Execute the full pipeline end-to-end."""
        import pandas as pd
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.metrics import accuracy_score, classification_report
        from sklearn.model_selection import train_test_split

        # 1. Load
        df = pd.read_csv(self.data_path)

        # 2. Clean
        df = df.dropna()
        df = df.drop_duplicates()
        if self.features:
            available = [c for c in self.features if c in df.columns]
            df = df[available + [self.target]]
        else:
            available = [c for c in df.columns if c != self.target]
        df = pd.get_dummies(df, drop_first=True)

        # 3. Split
        X = df.drop(columns=[self.target])
        y = df[self.target]
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=self.test_split, random_state=self.random_seed
        )

        # 4. Train
        model = RandomForestClassifier(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            random_state=self.random_seed,
        )
        model.fit(X_train, y_train)

        # 5. Evaluate
        y_pred = model.predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        report = classification_report(y_test, y_pred, output_dict=True)

        # 6. Save
        Path(self.model_dir).mkdir(parents=True, exist_ok=True)
        model_path = os.path.join(self.model_dir, "model.pkl")
        with open(model_path, "wb") as f:
            pickle.dump(model, f)

        # 7. Export results
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        result_path = os.path.join(self.output_dir, "results.json")
        with open(result_path, "w") as f:
            json.dump({"accuracy": acc, "report": report}, f, indent=2)

        # 8. Deploy (copy to deploy dir)
        deploy_dir = Path(self.deploy_target)
        if deploy_dir.exists():
            shutil.rmtree(str(deploy_dir))
        shutil.copytree(self.model_dir, str(deploy_dir))
        deploy_marker = deploy_dir / "deployed.txt"
        deploy_marker.write_text(f"Deployed at {__import__('datetime').datetime.now().isoformat()}")

        return {
            "accuracy": acc,
            "model_path": model_path,
            "result_path": result_path,
            "deploy_path": str(deploy_dir),
        }
