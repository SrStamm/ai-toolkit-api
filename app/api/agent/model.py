class Tool:
    def __init__(self, name: str, description: str, fn):
        self.name = name
        self.description = description
        self.fn = fn

    def execute(self, input: str) -> str:
        return self.fn(input)

