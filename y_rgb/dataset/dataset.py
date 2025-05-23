import os
from typing import Sequence, Union, Optional, Callable, List, Dict, Any
from datasets import Dataset, DatasetDict, IterableDataset, load_dataset, load_from_disk
import warnings

from .base_dataset import BaseDataset
from ..common.registry import registry


@registry.register_dataset("BaseMapDataset")
class BaseMapDataset(BaseDataset):
    def __init__(
        self,
        data_source: Union[Sequence, str, Dataset, DatasetDict],
        only_local: bool = False,
        process_fn: Optional[Union[Dict[str, Callable], Callable[..., Any]]] = None,
        filter_fn: Optional[Union[Dict[str, Callable], Callable[..., Any]]] = None,
        process_first: bool = True,
        process_batched: bool = True,
        filter_batched: bool = True,
        process_bs: int = 1,
        filter_bs: int = 1,
        metadata: Optional[Dict] = None,
        data_format: Optional[str] = None,
        split_ratios: Optional[tuple] = (0.8, 0.1, 0.1),
        *args,
        **kwargs
    ):
        super().__init__(
            data_source,
            process_fn,
            filter_fn,
            process_first,
            process_batched,
            filter_batched,
            process_bs,
            filter_bs,
            metadata,
            data_format
        )
        self.split_ratios = split_ratios
        self._set_dataset(data_source, only_local)

        # 自动数据集划分
        if split_ratios:
            if isinstance(self.dataset, DatasetDict):
                warnings.warn("DatasetDict对象已经包含了多个划分，自动划分将被忽略")
            if isinstance(self.dataset, Dataset):
                self.auto_split(split_ratios)

        if process_fn is None and filter_fn is None:
            pass
        else:
            self._prepare_data()


    def _set_dataset(self, data_source, only_local, data_format=None) -> Dataset or DatasetDict:
        # 加载数据集
        if isinstance(data_source, str):
            """return a Dataset object"""
            if os.path.exists(data_source):
                if os.path.isdir(data_source):
                    self.dataset = load_from_disk(data_source)
                else:
                    if data_format is None:
                        data_format = infer_data_format(data_source)
                        if data_format is None:
                            raise ValueError("无法推断数据格式，请通过data_format参数指定。")

                    self.dataset = load_dataset(
                        data_format,
                        # 本地加载数据集，我往往不手动分割数据集，所以默认加载train集实际就是全部数据
                        # 后续再分割
                        split = 'train',
                        data_files=data_source,
                    )
            else:
                """return a DatasetDict object"""
                # HuggingFace Hub 名称
                if isinstance(data_source, str):
                   self.dataset = from_hf_dataset(data_source, None, only_local)

        elif isinstance(data_source, Sequence):
            self.dataset = from_hf_dataset(data_source[0], data_source[1], only_local)
        elif isinstance(data_source, (Dataset, DatasetDict)):
            self.dataset = data_source
        else:
            raise ValueError("不支持的数据源类型，当前支持str, [str, str], Dataset, DatasetDict类型")


    def auto_split(self, ratios: tuple) -> DatasetDict:
        """

        :param ratios:
        :return:
        """
        """自动划分训练/验证/测试集"""
        if isinstance(self.dataset, DatasetDict):
            return

        train_ratio, val_ratio, test_ratio = ratios
        total = sum(ratios)
        train_size = train_ratio / total

        train_temp = self.dataset.train_test_split(test_size = 1 - train_size)
        temp = train_temp["test"]

        # 第二次划分：验证集和测试集
        val_test = temp.train_test_split(test_size = test_ratio / (val_ratio + test_ratio))

        self.dataset = DatasetDict(
            {
                "train": train_temp["train"],
                "valid": val_test["train"],
                "test": val_test["test"],
            }
        )


    def get_subset(self, split = None, n = 1, start = 0) -> "BaseMapDataset":
        """获取子集"""
        if isinstance(self.dataset, DatasetDict):
            assert split is not None, "split should be specified when dataset is a DatasetDict."
            return BaseMapDataset(
                data_source = self.dataset[split].select(
                    range(start, min(start + n, len(self.dataset[split])))
                ),
                process_fn = None,
                filter_fn = None,
                split_ratios = None,
                metadata = self.metadata
            )
        return BaseMapDataset(
            data_source = self.dataset.select(
                range(start, min(start + n, len(self)))
            ),
            process_fn = None,
            filter_fn = None,
            split_ratios = None,
            metadata = self.metadata
        )


    def get_split(self, split: str) -> Dataset:
        if isinstance(self.dataset, Dataset):
            raise Exception("Dataset对象没有划分，无法获取子集")
        return self.dataset[split]


    def __len__(self) -> int:
        return len(self.dataset)

    def __getitem__(self, idx: int):
        return self.dataset[idx]


    def sample(self, split, n=1, start = 0) -> Dataset:
        """快速采样"""
        if isinstance(self.dataset, DatasetDict):
            return self.dataset[split].select(
                range(start, min(start + n, len(self.dataset[split])))
            )
        return self.dataset.select(range(start, min(start + n, len(self))))


    @property
    def dataset_card(self) -> Dict:
        """生成数据集卡片"""
        return {
            **self.metadata,
            "splits": list(self.dataset.keys()) if isinstance(self.dataset, DatasetDict) else 'no split',
            "size": len(self) if isinstance(self.dataset, Dataset) else {
                split: len(self.dataset[split]) for split in self.dataset.keys()
            },
            "streaming": False,
        }


@registry.register_dataset("BaseIterableDataset")
class BaseIterableDataset(BaseDataset):
    def __init__(
        self,
        data_source: Union[str, Sequence, Dataset, DatasetDict],
        only_local: bool = False,
        process_fn: Optional[Union[Dict[str, Callable], Callable[..., Any]]] = None,
        filter_fn: Optional[Union[Dict[str, Callable], Callable[..., Any]]] = None,
        process_first: bool = True,
        process_batched: bool = True,
        filter_batched: bool = True,
        process_bs: int = 1,
        filter_bs: int = 1,
        metadata: Optional[Dict] = None,
        data_format: Optional[str] = None,
        *args,
        **kwargs
    ):
        super().__init__(
            data_source,
            process_fn,
            filter_fn,
            process_first,
            process_batched,
            filter_batched,
            process_bs,
            filter_bs,
            metadata,
        )
        self._set_dataset(data_source, data_format, only_local)
        self._prepare_data()


    def _set_dataset(self, data_source: Union[str, Sequence, Dataset, DatasetDict],
                     data_format: Optional[str] = None, only_local: bool = False):

        if isinstance(data_source, str):
            if os.path.exists(data_source):
                if os.path.isdir(data_source):
                    raise ValueError("流式模式不支持加载Dataset目录，请使用原始数据文件。")

                if data_format is None:
                    data_format = infer_data_format(data_source)
                    if data_format is None:
                        raise ValueError("无法推断数据格式，请通过data_format参数指定。")

                self.dataset = load_dataset(
                    data_format,
                    split = 'train',
                    data_files=data_source,
                    streaming=True
                )
            else:
                # 远程HuggingFace Hub
                self.dataset = from_hf_dataset(data_source, None, only_local, streaming = True)

        elif isinstance(data_source, Sequence):
            # 远程HuggingFace Hub
            self.dataset = from_hf_dataset(data_source[0], data_source[1], only_local, streaming=True)
        elif isinstance(data_source, (Dataset, DatasetDict)):
            self.dataset = data_source.to_iterable_dataset()
        elif isinstance(data_source, IterableDataset):
            self.dataset = data_source
        else:
            raise ValueError("不支持的数据源类型")


    def __iter__(self):
        yield from self.dataset


    @property
    def dataset_card(self) -> Dict:
        """生成数据集卡片"""
        return {
            **self.metadata,
            "streaming": True,
        }

    def save_to_disk(self, path: str):
        os.makedirs(path, exist_ok=True)
        self.save_case(path)
        self.save_card(path)

        warnings.warn("case和dataset card已保存，但是流式数据集不支持保存到磁盘, 请首先转换为MapStyleDataset")



def infer_data_format(path: str) -> Optional[str]:
    ext = os.path.splitext(path)[1].lower().lstrip('.')
    format_mapping = {
        'csv': 'csv',
        'json': 'json',
        'jsonl': 'json',
        'txt': 'text',
        'text': 'text',
        'tsv': 'csv'
    }
    return format_mapping.get(ext)


def from_hf_dataset(path: str, name, only_local, streaming = False) -> Dataset:
    if not only_local:
        dataset = load_dataset(path, name, streaming = streaming, trust_remote_code = True)
    else:
        dataset = load_dataset(path, name, streaming = streaming, trust_remote_code = True, local_files_only=True)
    return dataset
