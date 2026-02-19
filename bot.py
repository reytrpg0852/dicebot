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

def shorten_output(body, suffix=""):
    full_text = body
    if suffix:
        full_text += "\n" + suffix
    if len(full_text) <= 500:
        return full_text
    return body[:50] + "......\n" + suffix

def roll_dice(expression):
    matches = list(DICE_PATTERN.finditer(expression))
    if not matches:
        return expression, safe_eval(expression)

    expanded_expr = expression
    total_expr = expression

    for match in reversed(matches):
        count = int(match.group(1))
        sides = int(match.group(2))

        if count < 1 or count > MAX_DICE:
            return expression, None
        if sides < 1 or sides > MAX_SIDES:
            return expression, None

        rolls = [random.randint(1, sides) for _ in range(count)]
        roll_sum = sum(rolls)

        detail = f"{count}d{sides}(" + "+".join(map(str, rolls)) + ")"

        start, end = match.span()
        expanded_expr = expanded_expr[:start] + detail + expanded_expr[end:]
        total_expr = total_expr[:start] + str(roll_sum) + total_expr[end:]

    return expanded_expr, safe_eval(total_expr)

def roll_b_dice(expression):
    match = B_PATTERN.search(expression)
    if not match:
        return None, None, None

    count = int(match.group(1))
    sides = int(match.group(2))

    if count < 1 or count > MAX_DICE:
        return None, None, None
    if sides < 1 or sides > MAX_SIDES:
        return None, None, None

    rolls = [random.randint(1, sides) for _ in range(count)]
    detail = f"{count}b{sides}(" + ",".join(map(str, rolls)) + ")"

    compare_match = COMPARE_PATTERN.search(expression)
    success = None

    if compare_match:
        op, target = compare_match.groups()
        target = int(target)
        success = sum(1 for r in rolls if eval(f"{r}{op}{target}"))
        detail = detail + f"{op}{target}"

    return detail, rolls, success

@bot.command()
async def r(ctx, *, arg=None):
    mention = ctx.author.mention
    expression = (arg or "1d100").strip()

    if B_PATTERN.search(expression):
        detail, rolls, success = roll_b_dice(expression)
        if detail is None:
            return

        compare_match = COMPARE_PATTERN.search(expression)

        if compare_match:
            suffix = f"Success：**{success}**"
        else:
            suffix = ""

        result = shorten_output(detail, suffix)
        await ctx.send(f"{mention}\n{result}")
        return

    compare_match = COMPARE_PATTERN.search(expression)
    expanded_expr, total = roll_dice(expression)
    if total is None:
        return

    if compare_match:
        op, target = compare_match.groups()
        success = eval(f"{total}{op}{target}")
        suffix = f"Total：**{total}**\nResult：**{'Success' if success else 'Fail'}**"
    else:
        suffix = f"Total：**{total}**"

    result = shorten_output(expanded_expr, suffix)
    await ctx.send(f"{mention}\n{result}")

@bot.command()
async def rr(ctx, times: int, *, arg):
    mention = ctx.author.mention

    if times < 1 or times > MAX_RR:
        return

    expression = arg.strip()

    if B_PATTERN.search(expression):
        compare_match = COMPARE_PATTERN.search(expression)
        lines = []
        total_success = 0

        for _ in range(times):
            detail, rolls, success = roll_b_dice(expression)
            if detail is None:
                return

            lines.append(detail)

            if compare_match:
                lines.append(f"Success : **{success}**")
                total_success += success

        body = "\n".join(lines)

        if compare_match:
            suffix = f"Total Success：**{total_success}**"
        else:
            suffix = ""

        result = shorten_output(body, suffix)
        await ctx.send(f"{mention}\n{result}")
        return

    # ===== dダイス修正部分 =====
    compare_match = COMPARE_PATTERN.search(expression)
    lines = []
    total_sum = 0
    success_total = 0

    for _ in range(times):
        expanded_expr, total = roll_dice(expression)
        if total is None:
            return

        lines.append(expanded_expr)
        lines.append(f"Total : {total}")

        if compare_match:
            op, target = compare_match.groups()
            result = eval(f"{total}{op}{target}")
            lines.append(f"Result : {'Success' if result else 'Fail'}")
            if result:
                success_total += 1
        else:
            total_sum += total

    body = "\n".join(lines)

    if compare_match:
        suffix = f"Success : {success_total}"
    else:
        suffix = f"Grand Total：**{total_sum}**"

    result = shorten_output(body, suffix)
    await ctx.send(f"{mention}\n{result}")

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    print("DISCORD_TOKEN が設定されていません。")
    sys.exit(1)

bot.run(TOKEN)
