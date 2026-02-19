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

# ===== 事前コンパイル =====
DICE_PATTERN = re.compile(r"(\d+)d(\d+)")
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
# 安定版 roll_dice（後方置換）
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
    match = re.match(r"(\d+)b(\d+)(.*)", expression)
    if not match:
        return None, None

    count = int(match.group(1))
    sides = int(match.group(2))
    tail = match.group(3)

    rolls = [random.randint(1, sides) for _ in range(count)]

    if compare:
        success = sum(1 for r in rolls if eval(f"{r}{compare}"))
        return rolls, success

    if tail:
        results = [safe_eval(str(r) + tail) for r in rolls]
        return rolls, results

    return rolls, None


def apply_limit(text, final_line):
    if len(text) <= 500:
        return text
    return text[:50] + "…………\n" + final_line


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

            result = (
                f"{base_expr}({','.join(map(str, rolls))}){op}{target}\n"
                f"Result：**{success}success**"
            )
            await ctx.send(f"{mention}\n{result}")
            return

        rolls, results = roll_b_dice(expression)
        values = results if results else rolls
        output = f"**{expression}(" + ",".join(map(str, values)) + ")**"
        await ctx.send(f"{mention}\n{output}")
        return

    if compare_match:
        op, target = compare_match.groups()
        base_expr = expression.split(op)[0]

        expanded_expr, total = roll_dice(base_expr)
        success = eval(f"{total}{op}{target}")

        text = (
            f"{expanded_expr}\n"
            f"Total：**{total}**\n"
            f"**Result**：**{'Success' if success else 'Fail'}**"
        )
        await ctx.send(f"{mention}\n{text}")
        return

    expanded_expr, total = roll_dice(expression)
    text = f"{expanded_expr}\nTotal：**{total}**"
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

    for _ in range(times):

        if "b" in expression:

            if compare_match:
                op, target = compare_match.groups()
                base_expr = expression.split(op)[0]
                rolls, success = roll_b_dice(base_expr, op + target)

                output_lines.append(
                    f"{base_expr}({','.join(map(str, rolls))}){op}{target}"
                )
                output_lines.append(f"Result：**{success}success**")
                success_total += success
            else:
                rolls, results = roll_b_dice(expression)
                values = results if results else rolls
                output_lines.append(
                    f"**{expression}(" + ",".join(map(str, values)) + ")**"
                )

        else:
            if compare_match:
                op, target = compare_match.groups()
                base_expr = expression.split(op)[0]

                expanded_expr, total = roll_dice(base_expr)
                success = eval(f"{total}{op}{target}")

                output_lines.append(expanded_expr)
                output_lines.append(f"Total：**{total}**")
                output_lines.append(
                    f"**Result**：**{'Success' if success else 'Fail'}**"
                )
                if success:
                    success_total += 1
            else:
                expanded_expr, total = roll_dice(expression)
                output_lines.append(expanded_expr)
                output_lines.append(f"Total：**{total}**")
                total_sum += total

    final_line = ""

    if compare_match:
        final_line = f"Success：**{success_total}**"
        output_lines.append(final_line)
    elif "b" not in expression:
        final_line = f"Grand Total：**{total_sum}**"
        output_lines.append(final_line)

    full_text = "\n".join(output_lines)
    full_text = apply_limit(full_text, final_line)

    await ctx.send(f"{mention}\n{full_text}")


TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    print("DISCORD_TOKEN が設定されていません。")
    sys.exit(1)

bot.run(TOKEN)
