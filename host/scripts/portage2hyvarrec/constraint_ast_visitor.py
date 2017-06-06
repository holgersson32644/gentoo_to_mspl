'''
Module defining the AST visitor created by parsing the gentoo dependencies
'''

__author__ = "Michael Lienhardt & Jacopo Mauro"
__copyright__ = "Copyright 2017, Michael Lienhardt & Jacopo Mauro"
__license__ = "ISC"
__version__ = "0.1"
__maintainer__ = "Jacopo Mauro"
__email__ = "mauro.jacopo@gmail.com"
__status__ = "Prototype"

class ASTVisitor(object):
    """
    this is the base Visitr class for our AST
    """
    def DefaultValue(self):
        return None
    def CombineValue(self, value1, value2):
        return value1

    def visitRequired(self, ctx):
        return reduce(self.__mapvisitRequiredEL, ctx, self.DefaultValue())
    def visitRequiredEL(self, ctx):
        if ctx['type'] == "rsimple":
            return self.visitRequiredSIMPLE(ctx)
        elif ctx['type'] == "rcondition":
            return self.visitRequiredCONDITION(ctx)
        elif ctx['type'] == "rchoice":
            return self.visitRequiredCHOICE(ctx)
        elif ctx['type'] == "rinner":
            return self.visitRequiredINNER(ctx)
    def visitRequiredSIMPLE(self, ctx):
        return self.DefaultValue()
    def visitRequiredCONDITION(self, ctx):
        return reduce(self.__mapvisitRequiredEL, ctx['els'], self.visitCondition(ctx['condition']))
    def visitRequiredCHOICE(self, ctx):
        return reduce(self.__mapvisitRequiredEL, ctx['els'], self.DefaultValue())
    def visitRequiredINNER(self, ctx):
        return reduce(self.__mapvisitRequiredEL, ctx['els'], self.DefaultValue())

    def visitDepend(self, ctx):
        return reduce(self.__mapvisitDependEL, ctx, self.DefaultValue())
    def visitDependEL(self, ctx):
        if ctx['type'] == "dsimple":
            return self.visitDependSIMPLE(ctx)
        elif ctx['type'] == "dcondition":
            return self.visitDependCONDITION(ctx)
        elif ctx['type'] == "dchoice":
            return self.visitDependCHOICE(ctx)
        elif ctx['type'] == "dinner":
            return self.visitDependINNER(ctx)
    def visitDependSIMPLE(self, ctx):
        return self.visitAtom(ctx['atom'])
    def visitDependCONDITION(self, ctx):
        return reduce(self.__mapvisitDependEL, ctx['els'], self.visitCondition(ctx['condition']))
    def visitDependCHOICE(self, ctx):
        return reduce(self.__mapvisitDependEL, ctx['els'], self.DefaultValue())
    def visitDependINNER(self, ctx):
        return reduce(self.__mapvisitDependEL, ctx['els'], self.DefaultValue())

    def visitChoice(self, ctx):
        return self.DefaultValue()
    def visitCondition(self, ctx):
        return self.DefaultValue()

    def visitAtom(self, ctx):
        res = self.DefaultValue()
        if 'version_op' in ctx:
            res = self.CombineValue(res, self.visitVersion_op(ctx['version_op']))
        if 'slots' in ctx:
            res = self.CombineValue(res, self.visitSlot(ctx['slots']))
        if 'selection' in ctx:
            res = reduce(self.__mapvisitSelection, ctx['selection'], res)
        return res

    def visitVersion_op(self, ctx):
        return self.DefaultValue()
    def visitSlot(self, ctx):
        if ctx['type'] == "ssimple":
            return self.visitSlotSIMPLE(ctx)
        elif ctx['type'] == "sfull":
            return self.visitSlotFULL(ctx)
        elif ctx['type'] == "seq":
            return self.visitSlotEQ(ctx)
        elif ctx['type'] == "sstar":
            return self.visitSlotSTAR(ctx)
    def visitSlotSIMPLE(self, ctx):
        return self.DefaultValue()
    def visitSlotFULL(self, ctx):
        return self.DefaultValue()
    def visitSlotEQ(self, ctx):
        return self.DefaultValue()
    def visitSlotSTAR(self, ctx):
        return self.DefaultValue()

    def visitSelection(self, ctx):
        res = self.DefaultValue()
        if 'prefix' in ctx:
            res = self.CombineValue(res, self.visitPrefix(ctx['prefix']))
        if 'preference' in ctx:
            res = self.CombineValue(res, self.visitPreference(ctx['preference']))
        if 'suffix' in ctx:
            res = self.CombineValue(res, self.visitSuffix(ctx['suffix']))
        return res
    def visitPrefix(self, ctx):
        return self.DefaultValue()
    def visitPreference(self, ctx):
        return self.DefaultValue()
    def visitSuffix(self, ctx):
        return self.DefaultValue()
    def __mapvisitRequiredEL(self,x,y):
        return self.CombineValue(x, self.visitRequiredEL(y))
    def __mapvisitDependEL(self,x,y):
        return self.CombineValue(x, self.visitDependEL(y))
    def __mapvisitSelection(self,x,y):
        return self.CombineValue(x, self.visitSelection(y))