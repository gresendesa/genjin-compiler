import re

class Indenter:
  def __init__(self, lines):
    self.lines = lines
    self.level = []
    self.indentation = 0
    self.statements = [('IF','ELSEIF'),
                       ('IF','ELSE'),
                       ('IF','ENDIF'),
                       ('ELSEIF','ELSEIF'),
                       ('ELSEIF','ENDIF'),
                       ('ELSEIF','ELSE'),
                       ('ELSE','ENDIF'),
                       ('IFMATCHES','ELSE'),
                       ('IFMATCHES','ENDIF'),
                       ('IFMATCHES','ELSEIF'),
                       ('IFBEGINSWITH','ELSE'),
                       ('IFBEGINSWITH','ENDIF'),
                       ('IFBEGINSWITH','ELSEIF'),
                       ('IFENDSWITH','ELSE'),
                       ('IFENDSWITH','ENDIF'),
                       ('IFENDSWITH','ELSEIF'),
                       ('IFCONTAINS','ELSE'),
                       ('IFCONTAINS','ENDIF'),
                       ('IFCONTAINS','ELSEIF'),
                       ('FOR','NEXT'),
                       ('FOREACH','NEXT'),
                       ('DO','UNTIL'),
                       ('DO','WHILE'),
                       ('DO','LOOP'),
                       ('UNSAFE','ENDUNSAFE'),
                       ('$${','}$$')]

  def check_closing(self, line):
    """
      return <statement> if line close statement otherwise None
    """
    result = None
    if len(self.level):
      for statement in self.statements:
        current_level = self.level[len(self.level) - 1]["statement"]
        match = re.match(r'^[ \t\n\n]*({})\b.*'.format(statement[1]), line, re.IGNORECASE)
        if match is not None:
          groups = match.groups()
          if current_level.lower() == statement[0].lower() and len(groups) and groups[0].lower() == statement[1].lower():
            result = statement[1]
    return result

  def check_opening(self, line):
    """
      return <statement> if line open statement otherwise None
    """
    result = None
    for statement in self.statements:
      match = re.match(r'^[ \t\n\n]*({})\b.*'.format(statement[0]), line, re.IGNORECASE)
      if match is not None:
        groups = match.groups()
        if len(groups) and groups[0].lower() == statement[0].lower():
          result = statement[0]
    return result

  def indent(self):
    """

      Itera a linha L
      
      Se a linha L corresponde ao fechamento no nível atual
        sim: feche o nível atual (diminui o recuo)
      Aplique recuo à linha correspondente ao nível atual
      Se a linha L corresponde à abertura de um nível
        sim: abra um nível (aumenta o recuo)

      Adicione a linha ao buffer

    """
    indented_lines = []
    for index, line in enumerate(self.lines): 

      #print(line)

      checking = self.check_closing(line)
      if checking is not None:
        #print("closing {}".format(checking))
        self.level.pop()
        self.indentation -= 1

      indented_line = "{}{}".format('\t' * self.indentation, line.strip(' \n\t\r'))

      checking = self.check_opening(line)
      if checking is not None:
        #print("opening {}".format(checking))
        self.level.append({"statement": checking, "index": index})
        self.indentation += 1

      indented_lines.append(indented_line)

    indented_lines = ["{};".format(i) for i in indented_lines if i]
    #print(indented_lines)
    #print(self.level)

    if len(self.level):
      raise Exception("Code not balanced! Forget closing some block? Invalid build!")

    return '\n'.join(indented_lines).replace("$${;","$${").replace("}$$;","}$$")

  def __str__(self):
    return self.content

class Minifier:
  chars = 'abcdefghijklmnopqrstuvwxyz'
  def __init__(self, content):
    self.content = content
    self.content=self.content.replace('$${','$${;')

  def minify(self, remove_comments=True, inject_collons=True, remove_tabs_and_break_lines=True):
    content = self.remove_comments(content=self.content)
    content = self.inject_collons(content=content)
    content = self.remove_tabs_and_break_lines(content=content)
    return {'content': content}

  #https://codereview.stackexchange.com/questions/148305/remove-comments-from-c-like-source-code
  def remove_comments(self, content):
    COMMENTS = re.compile(r'''
      ((?<!https:)(?<!http:)//[^\n]*(?:\n|$))    # Everything between // and the end of the line/file
      |                     # or
      (/\*.*?\*/)           # Everything between /* and */
    ''', re.VERBOSE)
    return COMMENTS.sub('\n', content)

  def inject_collons(self, content):
    copy = content
    buffer=''
    for line in content.splitlines():
      p = re.compile(r".*?;[^A-Za-z0-9]*$", re.MULTILINE)
      q = re.compile(r".*(\$\$\{|\}\$\$)[^\w]*$", re.MULTILINE)
      if p.match(line) or q.match(line):
        buffer+=line
      else:
        if re.match('.*[A-Za-z0-9].*',line) and re.match('.*[^${}>][^A-Za-z0-9]*$', line):
          buffer+="{};".format(line)
    return buffer

  def remove_tabs_and_break_lines(self, content):
    return re.sub(r"(?<=;)(\s+)(?=[^\s])", "", content).strip()