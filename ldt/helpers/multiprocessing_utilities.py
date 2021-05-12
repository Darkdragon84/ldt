import logging
import os
import traceback

from multiprocessing import Process, JoinableQueue, Manager

WORKER_FINISH = "WORKER_FINISH"

logger = logging.getLogger("multiprocessing_tools")
logger.addHandler(logging.NullHandler())


def input_output_worker(processor, input_queue, output_queue=None):
    logger.info("starting process {}".format(os.getpid()))

    # call input_queue.get() until sentinel WORKER_FINISH retrieved
    for task in iter(input_queue.get, WORKER_FINISH):
        n, data = task
        try:
            result = processor(data)
            if output_queue is not None:
                output_queue.put((n, result))
            logger.info("{}/{} done".format(os.getpid(), n))
        except Exception as exc:
            traceback.print_exc()
            logger.error("error in process {}".format(os.getpid()), exc_info=exc)
        finally:
            input_queue.task_done()

    logger.info("process {} finishing".format(os.getpid()))
    input_queue.task_done()


def pmap(input_data, n_workers, data_processor_worker, post_processor_worker=None, default=None):
    input_queue = JoinableQueue()
    output_queue = Manager().Queue() if post_processor_worker is None else JoinableQueue()

    data_processes = [Process(target=data_processor_worker, args=(input_queue, output_queue)) for _ in range(n_workers)]
    for p in data_processes:
        p.start()

    if post_processor_worker is not None:
        post_process = Process(target=post_processor_worker, args=(output_queue,))
        post_process.start()

    n_data = 0
    for n, data in enumerate(input_data):
        input_queue.put((n, data))
        n_data += 1

    # put sentinel value to signal workers to finish (one per process)
    for _ in range(n_workers):
        input_queue.put(WORKER_FINISH)

    input_queue.join()

    if post_processor_worker is not None:
        output_queue.put(WORKER_FINISH)
        output_queue.join()
        return

    # if no postprocessor is given, retrieve results from output queue and return as list
    results = [default] * n_data
    n_extr = 0
    while not output_queue.empty():
        n, res = output_queue.get()
        results[n] = res
        n_extr += 1

    logger.info("{} out of {} extracted".format(n_extr, n_data))
    return results
