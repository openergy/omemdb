class Version:
    @classmethod
    def from_text(cls, text):
        text_l = text.split(".")
        if len(text_l) != 3:
            raise ValueError("wrong version format")
        major = int(text_l[0])
        minor = 0 if len(text_l) == 1 else int(text_l[1])
        patch = 0 if len(text_l) == 2 else int(text_l[2])
        return cls(major, minor, patch)

    def __init__(self, major, minor, patch):
        self.major = major
        self.minor = minor
        self.patch = patch

    @property
    def tuple(self):
        return self.major, self.minor, self.patch

    def __lt__(self, other):
        return self.tuple < other.tuple

    def __eq__(self, other):
        return self.tuple == other.tuple

    def __str__(self):
        return ".".join(str(i) for i in (self.major, self.minor, self.patch))
