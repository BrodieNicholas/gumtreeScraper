"""Testing Sandbox Code"""

def argumentIteration(a="", b="", c="", d=""):
    arguments = locals()
    print(arguments)

def argIteration2(a="", b="", c="", d=""):
    arguments = (a, b, c, d)
    print(arguments)

if __name__=="__main__":
    argIteration2("asdf", "kldks", d="akfk")