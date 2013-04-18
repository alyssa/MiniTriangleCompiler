#!/usr/bin/env python
#
# Parser for the mini triangle language

import ast
import scanner 

class ParserError(Exception):
    """ Parser error exception.

        pos: position in the input token stream where the error occurred.
        val: vale of token
        type: bad token type
    """

    def __init__(self, pos, val, type):
        self.pos = pos
        self.val = val
        self.type = type

    def __str__(self):
        return '(Found bad token %s(%s) at %d)' % (scanner.TOKENS[self.type], str(self.val), self.pos)

class Parser(object):
    """ Implement a scanner for the following token grammar:
    
        Program ::=  block-Command

        block-Command       ::=  if Expression then single-Command 
                                    else single-Command 
                             |   while Expression do single-Command 
                             |   let Declaration in single-Command 
                             |   begin Command end
               
        Command     ::=  single-Command (single-Command)* 

        single-Command      ::=  sec-Command ';' 
                             |   block-Command

        sec-Command ::=  Identifier (':=' Expression | '(' Param ')') 
                            
        Expression          ::= SecExpr (OPER_SEC SecExpr)*
                             |  Identifier '(' Param ')'

        
        SecExpr     ::= PriExpr (OPER_PRI PriExpr)*   
        
        primary-Expression  ::=  Integer-Literal
                             |   Identifier
                             |   Operator primary-Expression
                             |   '(' Expression ')'

        
        Declaration ::=  (sec-Declaration ';' | func-declaration) (sec-Declaration ';' | func-declaration) * 

        sec-Declaration     ::=  const Identifier ~ Expression
                             |   var Identifier : Identifier  

        func-declaration ::=   func Identifier '(' Param ')' ':' Identifier single-Command
        
        Param          ::=  single-Param  (',' single-Param ) *

        single-Param   ::=  Identifier ':' Type-denoter
                                          
        Type-denoter   ::=  Identifier    
    """

    def __init__(self, tokens):
        self.tokens = tokens
        self.curindex = 0
        self.curtoken = tokens[0]
        
    def parse(self):
        """ Program ::=  Command """
        e1 = self.parse_blockcommand()
        return ast.Program(e1)
        
    def parse_blockcommand(self):
        """ 
        block-Command ::=  if Expression then single-gen-Command
                            else single-gen-Command
                       |   while Expression do single-gen-Command
                       |   let Declaration in single-gen-Command
                       |   begin gen-Command end
        """
        token = self.token_current()
        if token.type == scanner.TK_IF:
            self.token_accept_any()
            expr = self.parse_expr()
            self.token_accept(scanner.TK_THEN)
            c1 = self.parse_singlecommand()
            self.token_accept(scanner.TK_ELSE)
            c2 = self.parse_singlecommand()
            c1 = ast.IfCommand(expr, c1, c2)
        elif token.type == scanner.TK_WHILE:
            self.token_accept_any()
            expr = self.parse_expr()
            self.token_accept(scanner.TK_DO)
            c1 = self.parse_singlecommand()
            c1 = ast.WhileCommand(expr, c1)
        elif token.type == scanner.TK_LET:
            self.token_accept_any()
            decl = self.parse_declaration()
            self.token_accept(scanner.TK_IN)
            c1 = self.parse_singlecommand()
            c1 = ast.LetCommand(decl, c1)
        elif token.type == scanner.TK_BEGIN:
            self.token_accept_any()            
            token = self.token_current()
            c1 = self.parse_command()
            self.token_accept(scanner.TK_END)            
        else:
            raise ParserError(self.curtoken.pos, self.curtoken.val, self.curtoken.type)
        return c1

    def parse_command(self):
        """ Command     ::=  single-Command (single-Command)* """
        token = self.token_current()
        block_types = [scanner.TK_IF, scanner.TK_WHILE, scanner.TK_LET, scanner.TK_BEGIN]

        if token.type in block_types:

            c1 = self.parse_blockcommand()
            token = self.token_current()
            if token.type != scanner.TK_EOT and token.type != scanner.TK_END:
                c2 = self.parse_command()
                c1 = ast.SequentialCommand(c1, c2)
        else:
            c1 = self.parse_seccommand()
            self.token_accept(scanner.TK_SEMICOLON)
            token = self.token_current()

            if token.type != scanner.TK_EOT and token.type != scanner.TK_END:
                c2 = self.parse_command()
                c1 = ast.SequentialCommand(c1, c2)
     
        return c1

    def parse_singlecommand(self):
        """
        single-Command      ::=  sec-Command ';' 
                             |   block
        """
        token = self.token_current()  
        block_types = [scanner.TK_IF, scanner.TK_WHILE, scanner.TK_LET, scanner.TK_BEGIN]
  
        if token.type in block_types:
            c1 = self.parse_blockcommand()
        else:
            c1 = self.parse_seccommand()
            self.token_accept(scanner.TK_SEMICOLON)

        return c1

    def parse_seccommand(self):
        """ 
        sec-Command ::=  Identifier (':=' Expression | '(' Param ')') 
                     |   return Expression
        """
        token = self.token_current()
        
        token_lookahead = self.token_lookahead()         
        if token_lookahead.type == scanner.TK_BECOMES:
            """ Identifier ':=' Expression """
            ident = self.parse_ident()   
            self.token_accept(scanner.TK_BECOMES) # parse becomes
            expr = self.parse_expr()
     
            c1 = ast.AssignCommand(ident, expr)
        elif token_lookahead.type == scanner.TK_LPAREN:
            """ Identifier '(' Param ')' """
            ident = token.val   # save ident name
            self.token_accept(scanner.TK_IDENTIFIER) # scan the token
            self.token_accept(scanner.TK_LPAREN) # accept left paren
            # change callcommand expression to param
          #  expr = self.parse_expr()
            expr = self.parse_param_expr()
            self.token_accept(scanner.TK_RPAREN)
     
           # self.token_accept(scanner.TK_SEMICOLON)

            c1 = ast.CallCommand(ident, expr)

        elif token.type == scanner.TK_RETURN:
            self.token_accept_any()
            expr = self.parse_expr()
            c1 = ast.ReturnCommand(expr)
        else:
            raise ParserError(self.curtoken.pos, self.curtoken.val, self.curtoken.type)
      
        return c1

    def parse_param_expr(self):
        token = self.token_current()
        e1 = self.parse_expr()
        p1 = ast.Parameter(e1, None)
        token = self.token_current()
        while token.type == scanner.TK_COMMA:
            self.token_accept_any()
            e2 = self.parse_expr()
            p2 = ast.Parameter(e2, None)
            p1 = ast.SequentialParameter(p1, p2)
            token = self.token_current()
        return p1

    def parse_expr(self):        
        """ Expression ::=  primary-Expression (Operator primary-Expression)* """
        token = self.token_current()        
        token_lookahead = self.token_lookahead()         
        if token_lookahead.type == scanner.TK_LPAREN:
            """ Identifier '(' Param ')' """
            ident = token.val   # save ident name
            self.token_accept(scanner.TK_IDENTIFIER) # scan the token
            self.token_accept(scanner.TK_LPAREN) # accept left paren
            expr = self.parse_param_expr()
            self.token_accept(scanner.TK_RPAREN)
    
            e1 = ast.CallCommand(ident, expr)
        else:
            e1 = self.parse_secexpr()
            token = self.token_current()

            while token.type == scanner.TK_OPERATOR and token.val in ['+', '-', '<', '>', '=']:
                oper = token.val
                self.token_accept_any()
                e2 = self.parse_secexpr()
                e1 = ast.BinaryExpression(e1, oper, e2)    
                token = self.token_current()
            

        return e1

    def parse_secexpr(self):
        """ SecExpr :== PriExpr (OPER_PRI PriExpr)*"""
        e1 = self.parse_priexpr()
        token = self.token_current()
        while token.type == scanner.TK_OPERATOR and token.val in ['*', '/', '\\']:
            oper = token.val
            self.token_accept_any()
            e2 = self.parse_priexpr()
            token = self.token_current()
            e1 = ast.BinaryExpression(e1, oper, e2)
        return e1
    
    def parse_priexpr(self):
        """ 
        primary-Expression ::=  Integer-Literal
                            |   Identifier
                            |   Operator primary-Expression
                            |   '(' Expression ')'
        """
        token = self.token_current()
        if token.type == scanner.TK_INTLITERAL:
            e1 = ast.IntegerExpression(token.val)
            self.token_accept_any()
        elif token.type == scanner.TK_IDENTIFIER:
            e1 = self.parse_ident()
            e1 = ast.VnameExpression(e1)
        elif token.type == scanner.TK_OPERATOR:
            oper = token.val
            self.token_accept_any()
            expr = self.parse_priexpr()
            e1 = ast.UnaryExpression(oper, expr)
        elif token.type == scanner.TK_LPAREN:
            self.token_accept_any()
            e1 = self.parse_expr()
            self.token_accept(scanner.TK_RPAREN)
        else:
            raise ParserError(self.curtoken.pos, self.curtoken.val, self.curtoken.type)

        return e1

    def parse_declaration(self):
        """ 
        Declaration ::=  sec-Declaration ';' | func-declaration (sec-Declaration ';' | func-declaration) * 

        """
        token = self.token_current()
        
        if token.type in [scanner.TK_VAR, scanner.TK_CONST]:
            c1 = self.parse_secdeclaration()
            self.token_accept(scanner.TK_SEMICOLON)
            if token.type != scanner.TK_EOT and token.type != scanner.TK_IN:
                c2 = self.parse_declaration()
                c1 = ast.SequentialDeclaration(c1, c2)
            return c1
        elif token.type == scanner.TK_FUNC:
            c1 = self.parse_funcdeclaration()
            if token.type != scanner.TK_EOT and token.type != scanner.TK_IN:
                c2 = self.parse_declaration()
                c1 = ast.SequentialDeclaration(c1, c2)
            return c1

    def parse_secdeclaration(self):
        """
        sec-Declaration ::=  const Identifier ~ Expression 
                            |   var Identifier : Identifier                      
        """
        token = self.token_current()
        if token.type == scanner.TK_CONST:
            self.token_accept_any()
            ident = self.token_current().val
        
            self.token_accept(scanner.TK_IDENTIFIER)
            self.token_accept(scanner.TK_IS)
            expr = self.parse_expr()
            return ast.ConstDeclaration(ident, expr)
        elif token.type == scanner.TK_VAR:
            self.token_accept_any()
            ident = self.token_current().val
            self.token_accept(scanner.TK_IDENTIFIER)
            self.token_accept(scanner.TK_COLON)
            type_denoter = self.parse_typedenoter()
            return ast.VarDeclaration(ident, type_denoter)
        else:
            raise ParserError(self.curtoken.pos, self.curtoken.val, self.curtoken.type)
    
    def parse_funcdeclaration(self):
        self.token_accept_any() # accept the func keyword
        tk_ident = self.token_current()
        self.token_accept(scanner.TK_IDENTIFIER)
        self.token_accept(scanner.TK_LPAREN)
        param = self.parse_param()
        self.token_accept(scanner.TK_RPAREN)
        self.token_accept(scanner.TK_COLON)
        func_type = self.parse_typedenoter()
        command = self.parse_singlecommand()
        decl = ast.FunctionDeclaration(tk_ident.val, param, func_type, command)
        return decl

    def parse_param(self):
        tk_argident = self.token_current().val
        self.token_accept(scanner.TK_IDENTIFIER)
        self.token_accept(scanner.TK_COLON)
        arg_type = self.parse_typedenoter()
        p1 = ast.Parameter(tk_argident, arg_type)
        token = self.token_current()
        
        while token.type == scanner.TK_COMMA:
            self.token_accept_any()
            tk_argident = self.token_current().val
            
            self.token_accept(scanner.TK_IDENTIFIER)

            self.token_accept(scanner.TK_COLON)
            arg_type = self.parse_typedenoter()
            p2 = ast.Parameter(tk_argident, arg_type)
            p1 = ast.SequentialParameter(p1, p2)
            token = self.token_current()

        return p1

    def parse_typedenoter(self):
        """ Type-denoter       ::=  Identifier """
        token = self.token_current()
        v = ast.TypeDenoter(token.val)
        self.token_accept_any()
        return v

    def parse_ident(self):
        """ V-name             ::=  Identifier """
        token = self.token_current()
        v = ast.Vname(token.val)
        self.token_accept_any()
        return v
        
    def token_current(self):
        return self.curtoken
    
    def token_lookahead(self):
        return self.tokens[self.curindex + 1]
        
    def token_accept_any(self):
        # Do not increment curindex if curtoken is TK_EOT.
        if self.curtoken.type != scanner.TK_EOT:
            self.curindex += 1
            self.curtoken = self.tokens[self.curindex]

    def token_accept(self, type):
        if self.curtoken.type != type:
            raise ParserError(self.curtoken.pos, self.curtoken.val, self.curtoken.type)
        self.token_accept_any()
    
if __name__ == '__main__':
    pass