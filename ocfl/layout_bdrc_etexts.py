import os
import re

import codecs

from .digest import string_digest
from .layout import Layout, LayoutException


def _remove_prefixes(object_id, delimiters):
    rightmost_idx = -1
    for delimiter in delimiters:
        # ignore empty string
        if len(delimiter) > 0:
            delimiter_idx = object_id.rfind(delimiter)+len(delimiter)
            # don't use breaking points that would give an empty object id
            if delimiter_idx < len(object_id):
                rightmost_idx = max(rightmost_idx, delimiter_idx)
    if rightmost_idx > 0:
        return object_id[rightmost_idx:]
    return object_id


def _percent_encode(c):
    """Return % encoded version of string c."""
    c_bytes = c.encode("utf8")
    s = ""
    for b in c_bytes:
        s += "%" + codecs.encode(bytes([b]), encoding="hex_codec").decode("utf8")
    return s


def _get_encapsulation_directory(object_id, digest):
    """Return directory to encapsulate object."""
    d = ""
    for c in object_id:
        if re.match(r"[A-Za-z0-9-_]{1}", c):
            d += c
        else:
            d += _percent_encode(c)
    if len(d) > 100:
        return f"{d[:100]}-{digest}"
    return d


def _id_to_path(identifier, digest_algorithm, tuple_size, number_of_tuples, delimiters):
    """Return storage path from identifier."""
    identifier = _remove_prefixes(identifier, delimiters)
    digest = string_digest(identifier, digest_algorithm)
    digest = digest.lower()  # Not necessary for current digests
    path = ""
    for i in range(number_of_tuples):
        tuple = digest[i * tuple_size:i * tuple_size + tuple_size]
        path = os.path.join(path, tuple)
    encapsulation_directory = _get_encapsulation_directory(identifier, digest=digest)
    path = os.path.join(path, encapsulation_directory)
    return path


class Layout_BDRC_etexts(Layout):
    """Class to support trivial identity layout."""

    def __init__(self):
        """Initialize."""
        super().__init__()
        self.digest_algorithm = "sha256"
        self.tuple_size = 3
        self.number_of_tuples = 3
        self.delimiters = []
        # Config
        self.NAME = "bdrc_etexts"
        self.DESCRIPTION = "Extension bdrc_etexts: Hashed Truncated N-tuple Trees with Prefix-Omitted Object ID Encapsulating Directory for OCFL Storage Hierarchies"
        self.PARAMS = {"digestAlgorithm": self.check_digest_algorithm,
                       "tupleSize": self.check_tuple_size,
                       "numberOfTuples": self.check_number_of_tuples,
                       "delimiters": self.check_delimiters}

    def check_digest_algorithm(self, value):
        """Check digestAlgorithm parameter.

        From extension:
            Description: The digest algorithm to apply to the OCFL object
              identifier; MUST be an algorithm that is allowed in the OCFL
              fixity block
            Type: string
            Constraints: Must not be empty
            Default: sha256

        Argument:
            value (str): digest algorithm name

        Raises:
            LayoutException: if the digest algorithm is not supported

        Sets the digest_algorithm property of this object as a side effect.
        """
        if value is None:
            raise LayoutException("digestAlgorithm parameter must be specified")
        try:
            string_digest("dummy_data", digest_type=value)
        except ValueError as e:
            raise LayoutException("digestAlgorithm parameter specifies unknown or unsupported digests %s (%s)" % (value, str(e)))
        self.digest_algorithm = value

    def check_tuple_size(self, value):
        """Check tuple size paremeter.

        From extension:
            Name: `tupleSize`
            Description: Indicates the size of the segments (in characters)
              that the digest is split into
            Type: number
            Constraints: An integer between 0 and 32 inclusive
            Default: 3

        Argument:
            value (int): integer value for tuple size in characters

        Raises:
            LayoutException: if the tuple size is not allowed

        Sets the tuple_size property of this object as a side effect.
        """
        if value is None:
            raise LayoutException("tupleSize parameter must be specified")
        if not isinstance(value, int) or value < 0 or value > 32:
            raise LayoutException("tupleSize parameter must be aninteger between 0 and 32 inclusive")
        self.tuple_size = value

    def check_number_of_tuples(self, value):
        """Check numberOfTuples parameter.

        From extension:
            Name: `numberOfTuples`
            Description: Indicates how many segments are used for path generation
            Type: number
            Constraints: An integer between 0 and 32 inclusive
            Default: 3

        Argument:
            value (int): integer value for number of tuples

        Raises:
            LayoutException: if the number of tuples is not allowed

        Sets the number_of_tuples property of this object as a side effect.
        """
        if value is None:
            raise LayoutException("numberOfTuples parameter must be specified")
        if not isinstance(value, int) or value < 0 or value > 32:
            raise LayoutException("numberOfTuples parameter must be aninteger between 0 and 32 inclusive")
        self.number_of_tuples = value

    def check_delimiters(self, value):
        if value:
            for d in value:
                if not isinstance(d, str) or len(d) < 1:
                    raise LayoutException("Bad layout configuration: delimiters must be strings of length at least 1")

    def check_full_config(self):
        """Check combined configuration parameters.

        From extension:
            If tupleSize is set to 0, then no tuples are created and numberOfTuples
            MUST also equal 0.
            The product of tupleSize and numberOfTuples MUST be less than or equal
            to the number of characters in the hex encoded digest.

        Raises:
            LayoutException: in the case that there is an error.
        """
        # Both zero if one zero
        if ((self.tuple_size == 0 and self.number_of_tuples != 0)
                or (self.tuple_size != 0 and self.number_of_tuples == 0)):
            raise LayoutException("Bad layout configuration: If tupleSize is set to 0, then numberOfTuples MUST also equal 0.")
        # Enough chars in digest
        n = len(string_digest("dummy_data", digest_type=self.digest_algorithm))
        if self.tuple_size * self.number_of_tuples > n:
            raise LayoutException("Bad layout configuration: The product of tupleSize and numberOfTuples MUST be less than or equal to the number of characters in the hex encoded digest.")
        

    @property
    def config(self):
        """Dictionary with config.json configuration for the layout extenstion."""
        return {"extensionName": self.NAME,
                "digestAlgorithm": self.digest_algorithm,
                "tupleSize": self.tuple_size,
                "numberOfTuples": self.number_of_tuples,
                "delimiters": self.delimiters}

    def identifier_to_path(self, identifier):
        """Convert identifier to path relative to root.

        Algorithm:
        1. The OCFL object identifier is encoded as UTF-8 and hashed using the
           specified digestAlgorithm.
        2. The digest is encoded as a lower-case hex string.
        3. Starting at the beginning of the digest and working forwards, the
           digest is divided into numberOfTuples tuples each containing
           tupleSize characters.
        4. The tuples are joined, in order, using the filesystem path separator.
        5. The OCFL object identifier is percent-encoded to create the
            encapsulation directory name. However, if this is > 100 characters
            then it is tuncated at 100 characters and then "-" and the digest
            appended (so it would be 165 chars with sha256).
        6. The encapsulation directory name is joined to the end of the path.
        """
        return _id_to_path(identifier=identifier,
                           digest_algorithm=self.digest_algorithm,
                           tuple_size=self.tuple_size,
                           number_of_tuples=self.number_of_tuples,
                           delimiters=self.delimiters)
