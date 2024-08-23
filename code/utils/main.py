# Main utils to train models flexibly
import logging
import torch
from transformers import (TrainingArguments, Trainer)
from utils.utils import (set_device, process_tokenizer,
                         load_tokenizer_model, load_and_split_dataset)
from dotenv import load_dotenv
load_dotenv()


def unpack_prefs(prefs: dict) -> dict:
    """
    Unpack the preferences dictionary into individual variables.

    Args:
        prefs (dict): The preferences dictionary.

    Returns: dict
    """
    epochs = prefs['epochs']
    learning_rate = prefs['learning_rate']
    per_device_train_batch_size = prefs['per_device_train_batch_size']
    per_device_eval_batch_size = prefs['per_device_eval_batch_size']
    weight_decay = prefs['weight_decay']
    strategy = prefs['strategy']
    grad_acc_steps = prefs['gradient_accumulation_steps']

    return (epochs, learning_rate, per_device_train_batch_size,
            per_device_eval_batch_size, weight_decay, strategy,
            grad_acc_steps)


def train_model(tokenizer, model, device: torch.device, 
                prefs: dict, train_dataset, eval_dataset=None,
                model_save_name: str=None, save_model: bool=False,
                push_to_hub: bool=False, fine_tune: bool=False) -> None:
    """
    Train or fine-tune the model on the given dataset.

    Args:
        tokenizer: The tokenizer for the model.
        model: The model to train.
        device (torch.device): The device to train the model on.
        prefs (dict): The preferences dictionary.
        train_dataset: The training dataset.
        eval_dataset: The evaluation dataset.
        model_save_name (str): The name to save the model as.
        save_model (bool): Whether to save the model.
        push_to_hub (bool): Whether to push the model to the Hugging Face Hub.
        fine_tune (bool): Whether to fine-tune the model.
    
    Returns: None
    """
    # Unpack preferences
    epochs, learning_rate, per_device_train_batch_size, \
        per_device_eval_batch_size, weight_decay, strategy, \
        grad_acc_steps = unpack_prefs(prefs)

    output_dir = f"./{model_save_name}_fine_tuning" if fine_tune else f"./{model_save_name}"
    logging_dir = f"./logs_{model_save_name}_fine_tuning" if fine_tune else f"./logs_{model_save_name}"

    training_args = TrainingArguments(
        output_dir=output_dir,
        logging_dir=logging_dir,
        logging_strategy=strategy,
        logging_steps=100,
        eval_strategy=strategy if eval_dataset else "no",
        learning_rate=learning_rate,
        per_device_train_batch_size=per_device_train_batch_size,
        per_device_eval_batch_size=per_device_eval_batch_size,
        num_train_epochs=epochs,
        weight_decay=weight_decay,
        push_to_hub=push_to_hub,
        gradient_accumulation_steps=grad_acc_steps,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        tokenizer=tokenizer
    )

    trainer.train()

    if push_to_hub:
        trainer.push_to_hub(model_save_name)

    # Save the model and tokenizer
    if save_model:
        model.save_pretrained(model_save_name)
        tokenizer.save_pretrained(model_save_name)
        logging.info(
            f"{'Fine-tuning' if fine_tune else 'Training'} "
            f"completed and model saved as {model_save_name}"
        )
    else:
        logging.info(
            f"{'Fine-tuning' if fine_tune else 'Training'} "
            f"completed, model not saved"
        )


def train_model_pipeline(dataset_source: str,
                         dataset_identifier: str,
                         model_save_name: str,
                         save_model: bool,
                         prefs: dict,
                         max_train_samples: int = None,
                         max_test_samples: int = None,
                         load_pretrained_model: str = None,
                         push_to_hub: bool = False) -> None:
    """
    Generalized function to train or further train a T5 model.

    Args:
        dataset_source (str): Source of the dataset ('huggingface' or 'local').
        dataset_identifier (str): The dataset name or local path.
        model_save_name (str): Name to save the trained model.
        save_model (bool): Whether to save the model.
        prefs (dict): Training preferences such as epochs, learning rate, etc.
        max_train_samples (int, optional): Maximum number of training samples.
        max_test_samples (int, optional): Maximum number of testing samples.
        load_pretrained_model (str, optional): Path to a pre-trained model.
        push_to_hub (bool): Whether to push the model to the Hugging Face Hub.

    Returns:
        None
    """
    device = set_device()
    model_name = (f"google/flan-t5-base" 
                  if not load_pretrained_model else load_pretrained_model)

    tokenizer, model = load_tokenizer_model(model_name, device)
    train_dataset, test_dataset = load_and_split_dataset(
        source=dataset_source, dataset_identifier=dataset_identifier,
        max_train_samples=max_train_samples, max_test_samples=max_test_samples)

    tokenized_train_dataset, tokenized_test_dataset = process_tokenizer(
        tokenizer, train_dataset, test_dataset)

    # Train the model
    train_model(tokenizer, model, device, prefs,
                tokenized_train_dataset, tokenized_test_dataset,
                model_save_name, save_model=save_model, push_to_hub=push_to_hub)
