import discord
from discord.ext import commands
import random
import re
import ast
import operator
import os
import sys

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

MAX_RR = 100
MAX_DICE = 1000
MAX_SIDES = 1000

DICE_PATTERN = re.compile(r"(\d+)d(\d+)")
B_PATTERN = re.compile(r"(\d+)b(\d+)")
COMPARE_PATTERN = re.compile(r"(>=|<=|==|>|<)(\d+)")

operators = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg
}

def safe_eval(expr):
    def _eval(node):
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.BinOp):
            return operators[type(node.op)](_eval(node.left), _eval(node.right))
        elif isinstance(node, ast.UnaryOp):
            return operators[type(node.op)](_eval(node.operand))
        raise TypeError(node)

    return _eval(ast.parse(expr, mode="eval").body)

# =========================
# roll_dice
# =========================
def roll_dice(expression):

    matches = list(DICE_PATTERN.finditer(expression))
    if not matches:
        return expression, safe_eval(expression)

    expanded_expr = expression
    total_expr = expression

    for match in reversed(matches):
        count = int(match.group(1))
        sides = int(match.group(2))

        # 上限制御
        if count < 1 or count > MAX_DICE:
            return expression, None
        if sides < 1 or sides > MAX_SIDES:
            return expression, None

        rolls = [random.randint(1, sides) for _ in range(count)]
        roll_sum = sum(rolls)

        if count == 1:
            detail = f"{count}d{sides}({rolls[0]})"
        else:
            detail = f"{count}d{sides}(" + "+".join(map(str, rolls)) + ")"

        start, end = match.span()
        expanded_expr = expanded_expr[:start] + detail + expanded_expr[end:]
        total_expr = total_expr[:start] + str(roll_sum) + total_expr[end:]

    return expanded_expr, safe_eval(total_expr)


def roll_b_dice(expression, compare=None):
    match = B_PATTERN.match(expression)
    if not match:
        return None, None

    count = int(match.group(1))
    sides = int(match.group(2))

    # 上限制御
    if count < 1 or count > MAX_DICE:
        return None, None
    if sides < 1 or sides > MAX_SIDES:
        return None, None

    rolls = [random.randint(1, sides) for _ in range(count)]

    if compare:
        success = sum(1 for r in rolls if eval(f"{r}{compare}"))
        return rolls, success

    return rolls, None


# =========================
# !r
# =========================
@bot.command()
async def r(ctx, *, arg=None):

    mention = ctx.author.mention
    expression = (arg or "1d100").strip()

    compare_match = COMPARE_PATTERN.search(expression)

    if "b" in expression:
        if compare_match:
            op, target = compare_match.groups()
            base_expr = expression.split(op)[0]
            rolls, success = roll_b_dice(base_expr, op + target)

            if rolls is None:
                return

            result = f"{base_expr}({','.join(map(str, rolls))}){op}{target}\n"
            result += f"Result：**{success}success**"
            await ctx.send(f"{mention}\n{result}")
            return

        rolls, _ = roll_b_dice(expression)
        if rolls is None:
            return

        output = f"**{expression}(" + ",".join(map(str, rolls)) + ")**"
        await ctx.send(f"{mention}\n{output}")
        return

    if compare_match:
        op, target = compare_match.groups()
        base_expr = expression.split(op)[0]
        expanded_expr, total = roll_dice(base_expr)

        if total is None:
            return

        success = eval(f"{total}{op}{target}")
        text = f"{expanded_expr}\nTotal：**{total}**\n"
        text += f"**Result**：**{'Success' if success else 'Fail'}**"
        await ctx.send(f"{mention}\n{text}")
        return

    expanded_expr, total = roll_dice(expression)
    if total is None:
        return

    text = f"{expanded_expr}\nTotal：**{total}**"
    await ctx.send(f"{mention}\n{text}")


# =========================
# !rr
# =========================
@bot.command()
async def rr(ctx, times: int, *, arg):

    mention = ctx.author.mention

    if times < 1 or times > MAX_RR:
        return

    expression = arg.strip()
    compare_match = COMPARE_PATTERN.search(expression)

    output_lines = []
    total_sum = 0
    success_total = 0

    for _ in range(times):

        if compare_match:
            op, target = compare_match.groups()
            base_expr = expression.split(op)[0]
            expanded_expr, total = roll_dice(base_expr)

            if total is None:
                return

            success = eval(f"{total}{op}{target}")
            output_lines.append(expanded_expr)
            output_lines.append(f"Total：**{total}**")
            output_lines.append(f"**Result**：**{'Success' if success else 'Fail'}**")
            if success:
                success_total += 1
        else:
            expanded_expr, total = roll_dice(expression)
            if total is None:
                return

            output_lines.append(expanded_expr)
            output_lines.append(f"Total：**{total}**")
            total_sum += total

    if compare_match:
        output_lines.append(f"Success：**{success_total}**")
    else:
        output_lines.append(f"Grand Total：**{total_sum}**")

    await ctx.send(f"{mention}\n" + "\n".join(output_lines))


TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    print("DISCORD_TOKEN が設定されていません。")
    sys.exit(1)

bot.run(TOKEN)
