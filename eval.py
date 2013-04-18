# calc_eval.py

import scanner
import parser
import ast


class EvalError(Exception):
    """ Eval Error """

    def __init__(self, tree, expected):
        self.tree = tree
        self.expected = expected

    def __str__(self):
        return 'Error at ast node: %s expected: %s' % (str(self.tree), str(self.expected))

class Evaluator(object):

    def __init__(self, tree):
        self.tree = tree
        self.env = {}

    def run(self):
        if type(self.tree) is not ast.Program:
            raise EvalError(self.tree, ast.Program)
        if type(self.tree.command) is not ast.LetCommand:
            raise EvalError(self.tree.command, ast.LetCommand)

        return self.eval_command(self.tree.command)

    def eval_command(self, tree):

        if type(tree) is ast.LetCommand:
            return self.eval_let_command(tree)
        elif type(tree) is ast.SequentialCommand:
            return self.eval_seq_command(tree)
        elif type(tree) is ast.AssignCommand:
            return self.eval_assign_command(tree)
        elif type(tree) is ast.CallCommand:
            return self.eval_call_command(tree)
        elif type(tree) is ast.WhileCommand:
            return self.eval_while_command(tree)
        else:
            raise EvalError(tree, ast.Command)

    def eval_declaration(self, tree):

        if type(tree) is ast.VarDeclaration:
            self.env[tree.identifier] = [tree.type_denoter.identifier, None]
            return

        elif type(tree) is ast.ConstDeclaration:
            self.env[tree.identifier] = ['Integer', self.eval_expression(tree.expression)]

        elif type(tree) is ast.SequentialDeclaration:
            self.eval_declaration(tree.decl1)
            self.eval_declaration(tree.decl2)

    def eval_let_command(self, tree):
        self.eval_declaration(tree.declaration)
        self.eval_command(tree.command)

    def eval_seq_command(self, tree):
        self.eval_command(tree.command1)
        self.eval_command(tree.command2)

    def eval_assign_command(self, tree):
        e1 = self.eval_expression(tree.expression)
        self.env[tree.variable.identifier][1] = e1

    def eval_call_command(self, tree):
        e1 = self.eval_expression(tree.expression)
        func = tree.identifier
        if func == 'putint':
            print e1
        elif func == 'getint' and type(tree.expression) is ast.VnameExpression:
            v = input()
            name = tree.expression.variable.identifier
            self.env[name][1] = v
        else:
            raise EvalError(tree, 'putint')

    def eval_while_command(self, tree):
        expr = tree.expression
        cmd  = tree.command

        while True:
            expr_val = self.eval_expression(expr)
            if not expr_val:
                break
            self.eval_command(cmd)

    def eval_expression(self, tree):
        
        if type(tree) is ast.IntegerExpression:
            return tree.value
        elif type(tree) is ast.VnameExpression:
            return self.env[tree.variable.identifier][1]
        elif type(tree) is ast.UnaryExpression:
            if tree.operator == '-':
                return -(self.eval_expression(tree.expression))
            elif tree.operator == '+':
                return self.eval_expression(tree.expression)
            else:
                raise EvalError(tree, ['-', '+'])
        elif type(tree) is ast.BinaryExpression:
            e1 = self.eval_expression(tree.expr1)
            e2 = self.eval_expression(tree.expr2)
            val = eval('%s %s %s' % (e1, tree.oper, e2))
            return val
        else:
            raise EvalError(tree, [ast.IntegerExpression, ast.VnameExpression,
                                   ast.UnaryExpression, ast.BinaryExpression])


if __name__ == '__main__':
    progs = [ """let
                   var x: Integer;
                   var y: Integer;
                   var z: Integer
                 in
                   begin
                     getint(x);
                     y := 2;
                     z := x + y;
                     putint(z)
                   end
              """,
              """! Factorial
                 let var x: Integer;
                     var fact: Integer
                 in
                   begin
                     getint(x);
                     fact := 1;
                     while x > 0 do
                       begin
                         fact := fact * x;
                         x := x - 1
                       end;
                     putint(fact)
                   end
              """]

    for prog in progs:
        print '=============='
        print prog
        
        scanner_obj = scanner.Scanner(prog)
        
        try:
            tokens = scanner_obj.scan()
            print tokens
        except scanner.ScannerError as e:
            print e
            continue

        parser_obj = parser.Parser(tokens)

        try:
            tree = parser_obj.parse()
            print tree
        except parser.ParserError as e:
            print e
            print 'Not Parsed!'
            continue

        evaluator_obj = Evaluator(tree)
        evaluator_obj.run()
