import os
import fuse
from fuse import FUSE, Operations
import errno

class ConcatFS(Operations):
    def __init__(self, source_dir):
        self.source_dir = source_dir
        self.files = self._load_files()
        self.file_sizes = self._get_file_sizes()

    def _process_filename(self, filename):
        return f"chunks/{filename[0:2]}/{filename}"
    
    def _load_files(self):
        files = {}
        for file_name in os.listdir(self.source_dir):
            file_path = os.path.join(self.source_dir, file_name)
            if os.path.isfile(file_path):
                with open(file_path, 'r') as f:
                    hashes = [self._process_filename(line.strip()) for line in f]
                files[file_name] = hashes
        return files

    def _get_file_sizes(self):
        file_sizes = {}
        for file_name, files in self.files.items():
            cumulative_sizes = []
            total_size = 0
            for file_path in files:
                file_size = os.path.getsize(file_path)
                cumulative_sizes.append((total_size, total_size + file_size, file_path))
                total_size += file_size
            file_sizes[file_name] = cumulative_sizes
        return file_sizes

    def getattr(self, path, fh=None):
        if path == '/':
            st = dict(st_mode=(0o40755), st_nlink=2)
            return st
        file_name = path.lstrip('/')
        if file_name in self.file_sizes:
            total_size = self.file_sizes[file_name][-1][1]
            st = dict(st_mode=(0o100444), st_nlink=1, st_size=total_size)
            return st
        raise fuse.FuseOSError(errno.ENOENT)

    def open(self, path, flags):
        file_name = path.lstrip('/')
        if file_name not in self.files:
            raise fuse.FuseOSError(errno.ENOENT)
        return 0

    def read(self, path, size, offset, fh):
        file_name = path.lstrip('/')
        if file_name not in self.files:
            raise fuse.FuseOSError(errno.ENOENT)

        data = bytearray()
        remaining_size = size
        current_offset = offset

        for start, end, file_path in self.file_sizes[file_name]:
            if current_offset < end:
                with open(file_path, 'rb') as f:
                    f.seek(current_offset - start)
                    chunk = f.read(min(remaining_size, end - current_offset))
                    data.extend(chunk)
                    remaining_size -= len(chunk)
                    if remaining_size <= 0:
                        break
            current_offset = max(current_offset, end)

        return bytes(data)

    def readdir(self, path, fh):
        if path == '/':
            return ['.', '..'] + list(self.files.keys())
        raise fuse.FuseOSError(errno.ENOENT)

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Expose files as virtual files based on SHA1 hashes in a directory')
    parser.add_argument('source_dir', type=str, help='Directory containing files with SHA1 hashes')
    parser.add_argument('mount_point', type=str, help='Mount point for the virtual filesystem')

    args = parser.parse_args()

    fuse = FUSE(ConcatFS(args.source_dir), args.mount_point, foreground=True, allow_other=True)

if __name__ == '__main__':
    main()
