import os

EXTENSION = ".dwcache"

IMPLIES_FAILURE = 2
IMPLIES_SUCCESS = 1

class BadCacheFilename(Exception):
    def __init__(self, filename=""): self._filename = filename
    def __str__(self): return self._filename

class DWCacheFile:
    FILENAME_TEMPLATE = "{}_{}_{}_ft.dwcache"
    def __init__(self, cache, filename):
        self._cache = cache
        self._filename = filename
        try:
            assert filename.endswith(EXTENSION)
            d, w, kind, units = filename[0:-len(EXTENSION)].split("_")
            self._depth = int(d)
            self._width = int(w)
            self._is_yes = (kind == "yes")
            if not self._is_yes: assert kind == "no"
            assert units == "ft"
        except:
            raise BadCacheFilename(self._filename)
    def implies_about_cand(self, cand_depth, cand_width):
        if self._is_yes:
            if (cand_depth <= self._depth) and (cand_width <= self._width): return IMPLIES_SUCCESS
        else:
            if (cand_depth >= self._depth) and (cand_width >= self._width): return IMPLIES_FAILURE
    def filepath(self): return os.path.join(self._cache.cachedir(), self._filename)
    def get_values(self):
        with open(self.filepath(), 'r') as fh:
            out = [ line.strip() for line in fh.readlines() ]
        if out and not out[-1]: out.pop(-1)
        return out
    def store_values(self, values):
        value_count = 0
        with open(self.filepath(), 'a') as fh:
            for v in values:
                value_count += 1
                fh.write(str(v))
                fh.write('\n')
                print("WRITING TO CACHE:", str(v))
        print("Wrote {} records to '{}' ".format(value_count, self.filepath()))

class DWCache:
    def __init__(self, cachedir):
        self._cachedir = cachedir
        self.cache_key = None
    def cachedir(self): return self._cachedir
    def all_cache_files(self):
        for entry in os.scandir(self._cachedir):
            if not entry.is_dir(): yield DWCacheFile(self, entry.name)
    def retrieve_results(self, cand_depth, cand_width):
        """
        Returns tuple of WINNERS and LOSERS.
        """
        winners = []
        losers = []
        for cache_file in self.all_cache_files():
            applies = cache_file.implies_about_cand(cand_depth, cand_width)
            if applies is None: continue
            if applies == IMPLIES_FAILURE:
                losers.extend(cache_file.get_values())
            elif applies == IMPLIES_SUCCESS:
                winners.extend(cache_file.get_values())
            else:
                raise ValueError(applies)
        return winners, losers
    def store_winners(self, cand_depth, cand_width, winners):
        if type(cand_depth) is float: cand_depth = math.ceil(cand_depth)
        if type(cand_width) is float: cand_width = math.ceil(cand_width)
        fname = DWCacheFile.FILENAME_TEMPLATE.format(cand_depth, cand_width, "yes")
        DWCacheFile(self, fname).store_values(winners)
    def store_losers(self, cand_depth, cand_width, losers):
        if type(cand_depth) is float: cand_depth = math.floor(cand_depth)
        if type(cand_width) is float: cand_width = math.floor(cand_width)
        fname = DWCacheFile.FILENAME_TEMPLATE.format(cand_depth, cand_width, "no")
        DWCacheFile(self, fname).store_values(losers)
