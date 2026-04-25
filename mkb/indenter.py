import sys
from coder import Indenter, Minifier

if __name__ == "__main__":
    c = sys.stdin.read()
    print(Indenter(lines=Minifier(content=c).minify()['content'].split(';')).indent())