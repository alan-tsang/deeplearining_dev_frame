# adapted from https://github.com/open-mmlab/mmengine/blob/main/mmengine/dataset/utils.py
from typing import Any, Mapping, Sequence
from torch.utils.data._utils.collate import default_collate as torch_default_collate


def pseudo_collate(data_batch: Sequence) -> Any:
    """Convert list of data sampled from dataset into a batch of data, of which
    type consistent with the type of each data_itement in ``data_batch``.

    The default behavior of dataloader is to merge a list of samples to form
    a mini-batch of Tensor(s). However, in MMEngine, ``pseudo_collate``
    will not stack tensors to batch tensors, and convert int, float, ndarray to
    tensors.

    This code is referenced from:
    `Pytorch default_collate <https://github.com/pytorch/pytorch/blob/master/torch/utils/data/_utils/collate.py>`_.

    Args:
        data_batch (Sequence): Batch of data from <dataloader>.

    Returns:
        Any: Transversed Data in the same format as the data_itement of
        ``data_batch``.
    """
    data_item = data_batch[0]
    data_item_type = type(data_item)
    if isinstance(data_item, (str, bytes)):
        return data_batch
    elif isinstance(data_item, tuple) and hasattr(data_item, '_fields'):
        # named tuple
        return data_item_type(*(pseudo_collate(samples)
                                for samples in zip(*data_batch)))
    elif isinstance(data_item, Sequence):
        # check to make sure that the data_itements in batch have consistent size
        it = iter(data_batch)
        data_item_size = len(next(it))
        if not all(len(data_item) == data_item_size for data_item in it):
            raise RuntimeError(
                'each data_itement in list of batch should be of equal size')
        transposed = list(zip(*data_batch))

        if isinstance(data_item, tuple):
            return [pseudo_collate(samples)
                    for samples in transposed]
        else:
            try:
                return data_item_type(
                    [pseudo_collate(samples) for samples in transposed])
            except TypeError:
                # The sequence type may not support `__init__(iterable)`
                # (e.g., `range`).
                return [pseudo_collate(samples) for samples in transposed]
    elif isinstance(data_item, Mapping):
        return data_item_type({
            key: pseudo_collate([d[key] for d in data_batch])
            for key in data_item
        })
    else:
        return data_batch


def default_collate(data_batch: Sequence) -> Any:
    """Convert list of data sampled from dataset into a batch of data, of which
    type consistent with the type of each data_itement in ``data_batch``.

    Different from :func:`pseudo_collate`, ``default_collate`` will stack
    tensor contained in ``data_batch`` into a batched tensor with the
    first dimension batch size, and then move input tensor to the target
    device.

    This code is referenced from:
    `Pytorch default_collate <https://github.com/pytorch/pytorch/blob/master/torch/utils/data/_utils/collate.py>`_.

    Note:
        ``default_collate`` only accept input tensor with the same shape.

    Args:
        data_batch (Sequence): Data sampled from dataset.

    Returns:
        Any: Data in the same format as the data_itement of ``data_batch``, of which
        tensors have been stacked, and ndarray, int, float have been
        converted to tensors.
    """
    data_item = data_batch[0]
    data_item_type = type(data_item)

    if isinstance(data_item, (str, bytes)):
        return data_batch
    elif isinstance(data_item, tuple) and hasattr(data_item, '_fields'):
        # named_tuple
        return data_item_type(*(default_collate(samples)
                                for samples in zip(*data_batch)))
    elif isinstance(data_item, Sequence):
        # check to make sure that the data_itements in batch have
        # consistent size
        it = iter(data_batch)
        data_item_size = len(next(it))
        if not all(len(data_item) == data_item_size for data_item in it):
            raise RuntimeError(
                'each data_itement in list of batch should be of equal size')
        transposed = list(zip(*data_batch))

        if isinstance(data_item, tuple):
            return [default_collate(samples)
                    for samples in transposed]  # Compat with Pytorch.
        else:
            try:
                return data_item_type(
                    [default_collate(samples) for samples in transposed])
            except TypeError:
                # The sequence type may not support `__init__(iterable)`
                # (e.g., `range`).
                return [default_collate(samples) for samples in transposed]
    elif isinstance(data_item, Mapping):
        return data_item_type({
            key: default_collate([d[key] for d in data_batch])
            for key in data_item
        })
    else:
        return torch_default_collate(data_batch)
