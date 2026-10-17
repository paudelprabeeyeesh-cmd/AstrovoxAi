"""Local commands for managing small, experimental Neural Lab runs."""

import argparse
import json

from .datasets import DatasetStore
from .evaluation import evaluate_checkpoint, generate_text
from .experiments import list_experiments
from .registry import ModelRegistry
from .training import train_tiny_model


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    train = commands.add_parser("train", help="train a tiny model from a local UTF-8 text file")
    train.add_argument("--dataset", required=True)
    train.add_argument("--output", required=True)
    train.add_argument("--steps", type=int, default=10)
    train.add_argument("--seed", type=int, default=17)
    train.add_argument("--checkpoint-interval", type=int, default=5)
    train.add_argument("--context", type=int, default=32)
    train.add_argument("--hidden", type=int, default=16)
    train.add_argument("--layers", type=int, default=1)
    train.add_argument("--heads", type=int, default=2)
    train.add_argument("--batch-size", type=int, default=1)
    train.add_argument("--optimizer", choices=("adamw", "adam", "sgd"), default="adamw")
    train.add_argument("--budget-mib", type=int, default=256)
    train.add_argument("--reserve-mib", type=int, default=1536)
    train.add_argument("--resume")

    dataset = commands.add_parser("dataset", help="manage copied local text datasets")
    dataset_commands = dataset.add_subparsers(dest="dataset_command", required=True)
    add = dataset_commands.add_parser("add")
    add.add_argument("--root", required=True)
    add.add_argument("--file", required=True)
    add.add_argument("--provenance", default="User-provided local file")
    add.add_argument("--license-note", default="Unspecified; verify permission before use")
    list_data = dataset_commands.add_parser("list")
    list_data.add_argument("--root", required=True)
    delete = dataset_commands.add_parser("delete")
    delete.add_argument("--root", required=True)
    delete.add_argument("--dataset-id", required=True)
    delete.add_argument("--confirm-delete", action="store_true", help="confirm permanent removal from the local Neural Lab dataset store")

    evaluation = commands.add_parser("evaluate", help="measure next-token loss on a held-out split")
    evaluation.add_argument("--checkpoint", required=True)
    evaluation.add_argument("--dataset", required=True)
    evaluation.add_argument("--max-batches", type=int, default=32)

    generation = commands.add_parser("generate", help="sample text from an experimental checkpoint")
    generation.add_argument("--checkpoint", required=True)
    generation.add_argument("--prompt", required=True)
    generation.add_argument("--tokens", type=int, default=64)
    generation.add_argument("--temperature", type=float, default=1.0)
    generation.add_argument("--top-k", type=int)

    experiments = commands.add_parser("experiments", help="list saved job records")
    experiments.add_argument("--root", required=True)

    registry = commands.add_parser("models", help="register and select experimental checkpoints")
    registry_commands = registry.add_subparsers(dest="registry_command", required=True)
    register = registry_commands.add_parser("register")
    register.add_argument("--root", required=True)
    register.add_argument("--run-dir", required=True)
    register.add_argument("--name", required=True)
    register.add_argument("--dataset-provenance", required=True)
    list_models = registry_commands.add_parser("list")
    list_models.add_argument("--root", required=True)
    select = registry_commands.add_parser("select")
    select.add_argument("--root", required=True)
    select.add_argument("--model-id", required=True)
    rollback = registry_commands.add_parser("rollback")
    rollback.add_argument("--root", required=True)

    args = parser.parse_args()
    if args.command == "train":
        result = train_tiny_model(
            args.dataset, args.output, context_length=args.context, hidden_size=args.hidden,
            num_layers=args.layers, num_heads=args.heads, batch_size=args.batch_size,
            max_steps=args.steps, optimizer_name=args.optimizer, memory_budget_mib=args.budget_mib,
            reserve_memory_mib=args.reserve_mib, resume_from=args.resume, seed=args.seed,
            checkpoint_interval=args.checkpoint_interval,
        )
        print(json.dumps(result, indent=2))
    elif args.command == "dataset":
        store = DatasetStore(args.root)
        if args.dataset_command == "add":
            result = store.add_file(args.file, provenance=args.provenance, license_note=args.license_note)
        elif args.dataset_command == "list":
            result = store.list_datasets()
        else:
            store.delete(args.dataset_id, confirmed=args.confirm_delete)
            result = {"deleted": args.dataset_id}
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif args.command == "evaluate":
        print(json.dumps(evaluate_checkpoint(args.checkpoint, args.dataset, max_batches=args.max_batches), indent=2))
    elif args.command == "generate":
        print(generate_text(args.checkpoint, args.prompt, max_new_tokens=args.tokens,
                            temperature=args.temperature, top_k=args.top_k))
    elif args.command == "experiments":
        print(json.dumps(list_experiments(args.root), indent=2))
    else:
        registry = ModelRegistry(args.root)
        if args.registry_command == "register":
            result = registry.register_completed_run(args.run_dir, name=args.name,
                                                     dataset_provenance=args.dataset_provenance)
        elif args.registry_command == "list":
            result = registry.list_models()
        elif args.registry_command == "select":
            result = registry.select_experimental(args.model_id)
        else:
            result = registry.rollback_experimental_selection()
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
