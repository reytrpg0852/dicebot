import discord
import random
import re
import ast
import operator
import os

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# --------------------
# 安全な演算処理
# --------------------
operators = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg
}

def safe_eval(node):
    if isinstance(node, ast.Num):
        return node.n
    elif isinstance(node, ast.BinOp):
        return operators[type(node.op)](
            safe_eval(node.left),
            safe_eval(node.right)
        )
    elif isinstance(node, ast.UnaryOp):
        return operators[type(node.op)](
            safe_eval(node.operand)
        )
    else:
        raise TypeError(node)

# --------------------
# dダイス処理
# --------------------
dice_pattern = re.compile(r'(\d+)d(\d+)')

def parse_dice(expression):
    def roll(match):
        dice_count = int(match.group(1))
        dice_side = int(match.group(2))

        # 上限チェック（無反応）
        if dice_count < 1 or dice_count > 100:
            return match.group(0)
        if dice_side < 1 or dice_side > 1000:
            return match.group(0)

        rolls = [random.randint(1, dice_side) for _ in range(dice_count)]
        return f"{dice_count}d{dice_side}(" + "+".join(map(str, rolls)) + ")"

    return dice_pattern.sub(roll, expression)

# --------------------
# bダイス処理
# --------------------
b_pattern = re.compile(r'(\d+)b(\d+)')

def parse_b_dice(expression):
    def roll(match):
        dice_count = int(match.group(1))
        dice_side = int(match.group(2))

        # 上限チェック（無反応）
        if dice_count < 1 or dice_count > 100:
            return match.group(0)
        if dice_side < 1 or dice_side > 1000:
            return match.group(0)

        rolls = [random.randint(1, dice_side) for _ in range(dice_count)]
        return f"{dice_count}b{dice_side}(" + ",".join(map(str, rolls)) + ")"

    return b_pattern.sub(roll, expression)

# --------------------
# メイン処理
# --------------------
@client.event
async def on_message(message):
    if message.author.bot:
        return

    # ---- !r ----
    if message.content.startswith("!r"):
        content = message.content[2:].strip()
        if not content:
            content = "1d100"

        content = parse_dice(content)
        content = parse_b_dice(content)

        try:
            tree = ast.parse(content, mode='eval')
            result = safe_eval(tree.body)
            await message.channel.send(f"{content}\nTotal: {result}")
        except:
            return

    # ---- !rr ----
    if message.content.startswith("!rr"):
        parts = message.content.split()

        if len(parts) < 3:
            return

        try:
            repeat = int(parts[1])
        except:
            return

        # rr回数制限（無反応）
        if repeat < 1 or repeat > 100:
            return

        expression = " ".join(parts[2:])

        grand_total = 0
        outputs = []

        for _ in range(repeat):
            content = parse_dice(expression)
            content = parse_b_dice(content)

            try:
                tree = ast.parse(content, mode='eval')
                result = safe_eval(tree.body)
            except:
                return

            grand_total += result
            outputs.append(f"{content} = {result}")

        outputs.append(f"\nGrand Total: {grand_total}")
        await message.channel.send("\n".join(outputs))

client.run(TOKEN)
