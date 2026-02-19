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

# 正規表現事前コンパイル
DICE_PATTERN = re.compile(r"(\d+)d(\d+)")
B_PATTERN = re.compile(r"(\d+)b(\d+)(.*)")
COMPARE_PATTERN = re.compile(r"(>=|<=|==|>|<)(\d+)")

operators = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg
}

compare_ops = {
    ">": operator.gt,
    "<": operator.lt,
    ">=": operator.ge,
    "<=": operator.le,
    "==": operator.eq
}

def safe_eval(expr):
    def _eval(node):
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.BinOp):
            return operators[type(node.op)](_eval(node.left), _eval(node.right))
        elif isinstance(node, ast.UnaryOp):
            return operators[type(node.op)](_eval(node.operand))
        else:
            raise TypeError(node)

    node = ast.parse(expr, mode="eval")
    return _eval(node.body)

def roll_dice(expression):
    rolls_detail = []
    total_expr = expression

    for match in DICE_PATTERN.finditer(expression):
        count, sides = map(int, match.groups())
        rolls = [random.randint(1, sides) for _ in range(count)]
        rolls_detail.append(f"{count}d{sides}(" + "+".join(map(str, rolls)) + ")")
        total_expr = total_expr.replace(match.group(), str(sum(rolls)), 1)

    total = safe_eval(total_expr)
    return rolls_detail, total

def roll_b_dice(expression, compare=None):
    match = B_PATTERN.match(expression)
    if not match:
        return None, None

    count, sides, tail = match.groups()
    count = int(count)
    sides = int(sides)

    rolls = [random.randint(1, sides) for _ in range(count)]

    if compare:
        op, target = compare
        target = int(target)
        success = sum(1 for r in rolls if compare_ops[op](r, target))
        return rolls, success

    if tail:
        results = [safe_eval(str(r) + tail) for r in rolls]
        return rolls, results

    return rolls, None

def apply_limit(text, final_line):
    return text if len(text) <= 500 else text[:50] + "…………\n" + final_line

@bot.command()
async def r(ctx, *, arg):

    mention = ctx.author.mention
    expression = arg.strip()
    compare_match = COMPARE_PATTERN.search(expression)

    # bダイス判定（安全）
    if B_PATTERN.match(expression.split(">")[0].split("<")[0].split("=")[0]):

        if compare_match:
            op, target = compare_match.groups()
            base_expr = expression.split(op)[0]
            rolls, success = roll_b_dice(base_expr, (op, target))

            result = f"{base_expr}({','.join(map(str, rolls))}){op}{target}\n"
            result += f"Result：**{success}success**"
            await ctx.send(f"{mention}\n{result}")
            return

        rolls, results = roll_b_dice(expression)

        content = results if results else rolls
        output = f"**{expression}(" + ",".join(map(str, content)) + ")**"

        await ctx.send(f"{mention}\n{output}")
        return

    # dダイス
    if compare_match:
        op, target = compare_match.groups()
        base_expr = expression.split(op)[0]
        rolls_detail, total = roll_dice(base_expr)

        success = compare_ops[op](total, int(target))

        text = "\n".join(rolls_detail)
        text += f"\nTotal：**{total}**\n"
        text += f"**Result**：**{'Success' if success else 'Fail'}**"

        await ctx.send(f"{mention}\n{text}")
        return

    rolls_detail, total = roll_dice(expression)
    text = "\n".join(rolls_detail)
    text += f"\nTotal：**{total}**"
    await ctx.send(f"{mention}\n{text}")

@bot.command()
async def rr(ctx, times: int, *, arg):

    mention = ctx.author.mention

    if times > MAX_RR:
        await ctx.send(f"{mention}\n回数は最大{MAX_RR}回までです。")
        return

    expression = arg.strip()
    compare_match = COMPARE_PATTERN.search(expression)

    output_lines = []
    total_sum = 0
    success_total = 0

    is_b = B_PATTERN.match(expression.split(">")[0].split("<")[0].split("=")[0])

    for _ in range(times):

        if is_b:

            if compare_match:
                op, target = compare_match.groups()
                base_expr = expression.split(op)[0]
                rolls, success = roll_b_dice(base_expr, (op, target))

                output_lines.append(f"{base_expr}({','.join(map(str, rolls))}){op}{target}")
                output_lines.append(f"Result：**{success}success**")
                success_total += success
            else:
                rolls, results = roll_b_dice(expression)
                content = results if results else rolls
                output_lines.append(f"**{expression}(" + ",".join(map(str, content)) + ")**")

        else:

            if compare_match:
                op, target = compare_match.groups()
                base_expr = expression.split(op)[0]
                rolls_detail, total = roll_dice(base_expr)

                success = compare_ops[op](total, int(target))

                output_lines.extend(rolls_detail)
                output_lines.append(f"Total：**{total}**")
                output_lines.append(f"**Result**：**{'Success' if success else 'Fail'}**")

                if success:
                    success_total += 1
            else:
                rolls_detail, total = roll_dice(expression)
                output_lines.extend(rolls_detail)
                output_lines.append(f"Total：**{total}**")
                total_sum += total

    if compare_match:
        final_line = f"Success：**{success_total}**"
        output_lines.append(final_line)
    elif not is_b:
        final_line = f"Grand Total：**{total_sum}**"
        output_lines.append(final_line)
    else:
        final_line = ""

    full_text = "\n".join(output_lines)
    full_text = apply_limit(full_text, final_line)

    await ctx.send(f"{mention}\n{full_text}")

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    print("DISCORD_TOKEN が設定されていません。")
    sys.exit(1)

bot.run(TOKEN)
