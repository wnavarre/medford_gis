def get_matching_key(d, key_h, *key_t, strict=True):
    keys = (key_h,) + key_t
    if strict:
        matching_key_count = sum(k in d for k in keys)
        assert matching_key_count == 1
    for i in range(len(key_t)):
        k_i = keys[i]
        try:
            return d[k_i]
        except KeyError:
            continue
    return d[keys[-1]]
