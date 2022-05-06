from .mp4 import enumerate_atoms


class NoExifFound(Exception):
    pass


def heif_get_exif(path: str) -> bytes:
    item_id = None
    iloc = None
    entries = None

    for depth, pos, type, size, content, leaf in enumerate_atoms(path, parse_atoms=True, unparsed_data=True):

        if type == "infe":
            if content["item_type"] == b"Exif":
                item_id = content["item_ID"]

        elif type == "iloc":
            iloc = content

    if not item_id or not iloc:
        raise NoExifFound("No Exif info found")

    for item in iloc["items"]:
        if item["item_ID"] == item_id:
            entries = item["entries"]

    if not entries or len(entries) != 1:
        raise ValueError("Bad file")

    extent_offset = entries[0].extent_offset + 4
    extent_length = entries[0].extent_length

    with open(path, "rb") as fr:
        fr.seek(extent_offset)
        return fr.read(extent_length)


if __name__ == "__main__":
    import logging
    from argparse import ArgumentParser

    import piexif

    from genutility.args import is_dir

    parser = ArgumentParser()
    parser.add_argument("path", type=is_dir)
    parser.add_argument("-r", "--recursive", action="store_true")
    args = parser.parse_args()

    if args.recursive:
        it = args.path.rglob("*.heic")
    else:
        it = args.path.glob("*.heic")

    for path in it:
        relpath = path.relative_to(args.path)

        try:
            data = heif_get_exif(path)
        except NoExifFound:
            logging.info("%s: No Exif Found", relpath)
        except ValueError:
            logging.exception(relpath)
        except AssertionError as e:
            logging.error("%s: AssertionError: %s", relpath, e)
        else:
            exif = piexif.load(data)
            print(
                relpath,
                exif["0th"][271].decode("ascii"),
                exif["0th"][272].decode("ascii"),
                exif["0th"][piexif.ImageIFD.DateTime].decode("ascii"),
            )
