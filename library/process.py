from multiprocessing import Process, Queue
from typing import Any, Callable


def run_with_queue(func: Callable, queue: Queue, *args, **kwargs) -> None:
    result = func(*args, **kwargs)
    queue.put(result)


def run_as_process(func: Callable, *args, **kwargs) -> Any:

    queue = Queue()

    args = list(args)
    args.insert(0, func)
    args.insert(1, queue)
    args = tuple(args)

    process = Process(target=run_with_queue, args=args, kwargs=kwargs)
    process.start()
    process.join()
    return queue.get()
