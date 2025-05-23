import argparse
import os
import random
import string
import time
import threading
import signal
import sys
import multiprocessing
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

# version 0.05
# Global flag for interrupt
stop_requested = False

# Dictionary to track per-thread stats
thread_stats = defaultdict(lambda: {"files": 0, "bytes": 0, "time": 0.0})

def handle_interrupt(signum, frame):
    global stop_requested
    stop_requested = True
    print("\n[!] Interrupt received. Gracefully shutting down...")

signal.signal(signal.SIGINT, handle_interrupt)

# Convert human-readable size to bytes
def parse_size(size_str):
    units = {"kb": 1024, "mb": 1024**2, "b": 1}
    for unit in units:
        if size_str.lower().endswith(unit):
            return int(float(size_str[:-len(unit)]) * units[unit])
    raise ValueError("Invalid size format. Use e.g., 1mb, 500kb")

def random_filename(length=10):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def estimate_dimensions(target_size):
    pixels = target_size // 3
    side = int(pixels ** 0.5)
    return max(8, side), max(8, side)

def generate_patterned_payload(width, height):
    data = bytearray()
    for y in range(height):
        for x in range(width):
            r = (x * 255) // width
            g = (y * 255) // height
            b = ((x + y) * 127) % 256
            data.extend([r, g, b])
    return bytes(data)

def generate_fake_image(path, fileformat, target_size):
    width, height = estimate_dimensions(target_size)
    data = generate_patterned_payload(width, height)
    body = data[:target_size]

    if fileformat == 'jpg':
        width_bytes = width.to_bytes(2, byteorder='big')
        height_bytes = height.to_bytes(2, byteorder='big')
        header = (
            b'\xff\xd8' +
            b'\xff\xe1\x00\x16Exif\x00\x00' +
            b'MM\x00*\x00\x00\x00\x08\x00\x00' +
            b'\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00' +
            b'\xff\xdb\x00C\x00' + bytes([i for i in range(64)]) +
            b'\xff\xc0\x00\x11\x08' + height_bytes + width_bytes +
            b'\x03\x01\x11\x00\x02\x11\x01\x03\x11\x01' +
            b'\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' +
            b'\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00?\x00'
        )
        footer = b'\xff\xd9'
        with open(path, 'wb') as f:
            f.write(header)
            f.write(body[:max(0, target_size - len(header) - len(footer))])
            f.write(footer)

    elif fileformat == 'bmp':
        row_padded = (width * 3 + 3) & ~3
        filesize = 54 + row_padded * height
        bmp_header = bytearray(b'BM')
        bmp_header += filesize.to_bytes(4, 'little') + b'\x00\x00\x00\x00' + b'\x36\x00\x00\x00'
        bmp_header += b'\x28\x00\x00\x00' + width.to_bytes(4, 'little') + height.to_bytes(4, 'little')
        bmp_header += b'\x01\x00\x18\x00' + b'\x00\x00\x00\x00' + b'\x00\x00\x00\x00'
        bmp_header += b'\x13\x0B\x00\x00' + b'\x13\x0B\x00\x00' + b'\x00\x00\x00\x00' + b'\x00\x00\x00\x00'
        with open(path, 'wb') as f:
            f.write(bmp_header)
            for y in range(height):
                row = bytearray()
                for x in range(width):
                    i = (y * width + x) * 3
                    row.extend(data[i+2:i+3] + data[i+1:i+2] + data[i:i+1])
                padding = b'\x00' * (row_padded - width * 3)
                f.write(row + padding)

    elif fileformat == 'ppm':
        with open(path, 'wb') as f:
            header = f'P6\n{width} {height}\n255\n'.encode('ascii')
            f.write(header + data)

    else:
        with open(path, 'wb') as f:
            f.write(os.urandom(target_size))

def generate_file(index, total, writepath, prefix, fileformat, min_size, max_size, verbose, batchid):
    global stop_requested
    if stop_requested:
        return 0

    thread_name = threading.current_thread().name
    filename = f"{prefix}{random_filename()}.{fileformat}"
    file_path = os.path.join(writepath, filename)

    target_size = random.randint(min_size, max_size)
    start = time.time()
    generate_fake_image(file_path, fileformat, target_size)
    actual_size = os.path.getsize(file_path)
    elapsed = time.time() - start

    thread_stats[thread_name]["files"] += 1
    thread_stats[thread_name]["bytes"] += actual_size
    thread_stats[thread_name]["time"] += elapsed

    if verbose:
        print(f"[{thread_name}] [{index + 1}/{total}] Generated {file_path} ({actual_size} bytes) in {elapsed:.2f}s BatchID: {batchid}")
    return actual_size

def main():
    global stop_requested

    parser = argparse.ArgumentParser(description="Generate simple valid image files.")
    parser.add_argument('--filecount', type=int, required=True, help='Number of images to generate')
    parser.add_argument('--filesize', type=str, required=True, help='File size range e.g., 1mb-3mb (not exact)')
    parser.add_argument('--fileformat', type=str, default='jpg', help='File format e.g., jpg, bmp, ppm')
    parser.add_argument('--filenameprefix', type=str, default='', help='Prefix for the generated filenames')
    parser.add_argument('--batchid', type=str, default='', help='Batch identifier for filenames (optional)')
    parser.add_argument('--verbose', action='store_true', help='Display progress and statistics')
    parser.add_argument('--writepath', type=str, default='output_images', help='Directory to write files to')
    parser.add_argument('--threads', type=int, default=multiprocessing.cpu_count(), help='Number of threads to use')
    args = parser.parse_args()

    min_size_str, max_size_str = args.filesize.lower().split('-')
    min_size = parse_size(min_size_str)
    max_size = parse_size(max_size_str)

    if args.batchid:
        args.filenameprefix = f"{args.batchid}_{args.filenameprefix}"

    os.makedirs(args.writepath, exist_ok=True)

    start_time = time.time()
    total_size = 0
    completed_tasks = 0
    BATCH_SIZE = 100

    try:
        with ThreadPoolExecutor(max_workers=args.threads) as executor:
            for batch_start in range(0, args.filecount, BATCH_SIZE):
                futures = [
                    executor.submit(generate_file, i, args.filecount, args.writepath, args.filenameprefix,
                                    args.fileformat.lower(), min_size, max_size, args.verbose, args.batchid)
                    for i in range(batch_start, min(batch_start + BATCH_SIZE, args.filecount))
                ]
                for future in as_completed(futures):
                    if stop_requested:
                        break
                    total_size += future.result()
                    completed_tasks += 1
                if stop_requested:
                    break

    except KeyboardInterrupt:
        stop_requested = True

    duration = time.time() - start_time
    if args.verbose:
        avg_size = total_size / completed_tasks if completed_tasks else 0
        print("\n--- Statistics ---")
        print(f"Generated files: {completed_tasks}")
        print(f"Average size: {avg_size:.2f} bytes")
        print(f"Total time: {duration:.2f} seconds")
        print("\n--- Per Thread Stats ---")
        for thread, stats in sorted(thread_stats.items()):
            print(f"{thread}: {stats['files']} files, {stats['bytes']} bytes, {stats['time']:.2f}s total")

if __name__ == '__main__':
    main()
