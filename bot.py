import discord
import random
import re
import ast
import operator
import os

TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(intents=intents)

allowed_operators = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.USub: operator.neg
}

def safe_eval(expr):
    def eval_node(node):
        if isinstance(node, ast.Num):
            return node.n
        if isinstance(node, ast.UnaryOp):
            return allowed_operators[type(node.op)](eval_node(node.operand))
        if isinstance(node, ast.BinOp):
            return allowed_operators[type(node.op)](
                eval_node(node.left),
                eval_node(node.right)
            )
        raise ValueError("Invalid expression")

    node = ast.parse(expr, mode="eval").body
    return eval_node(node)

def roll_dice(n, m):
    return [random.randint(1, m) for _ in range(n)]

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if not message.content.startswith("!r"):
        return

    raw = message.content[2:].strip()

    if raw == "":
        expr = "1d100"
        comment = ""
    else:
        raw = raw.replace("　", " ")
        parts = raw.split(" ", 1)
        expr = parts[0]
        comment = parts[1] if len(parts) > 1 else ""

    try:
        # -------------------------
        # 比較処理（安全版）
        # -------------------------
        comparison_match = re.search(r"(>=|<=|==|>|<|=)", expr)
        comparator = None
        compare_value = None

        if comparison_match:
            comparator = comparison_match.group()
            left, right = expr.split(comparator, 1)
            compare_value = safe_eval(right)
            expr = left.strip()

        # -------------------------
        # ダイス展開（安定版）
        # -------------------------
        dice_pattern = r"(\d+)d(\d+)"

        display_expr = expr

        while True:
            match = re.search(dice_pattern, expr)
            if not match:
                break

            n, m = map(int, match.groups())
            rolls = roll_dice(n, m)
            total = sum(rolls)
            roll_text = "+".join(map(str, rolls))

            # 計算用式置換（1回だけ）
            expr = re.sub(dice_pattern, str(total), expr, count=1)

            # 表示用式置換（1回だけ）
            display_expr = re.sub(
                dice_pattern,
                f"{n}d{m}({roll_text})",
                display_expr,
                count=1
            )

        # -------------------------
        # 計算
        # -------------------------
        result = round(safe_eval(expr), 3)

        if result == int(result):
            result = int(result)

        # -------------------------
        # 比較判定
        # -------------------------
        compare_text = ""
        if comparator:
            if comparator in ["=", "=="]:
                success = result == compare_value
            elif comparator == ">":
                success = result > compare_value
            elif comparator == "<":
                success = result < compare_value
            elif comparator == ">=":
                success = result >= compare_value
            elif comparator == "<=":
                success = result <= compare_value

            compare_text = f"\nResult：{'Success' if success else 'Fail'}"

        # -------------------------
        # 出力（メンション復活）
        # -------------------------
        if comment:
            output = (
                f"{message.author.mention}\n"
                f"{comment}：{display_expr}\n"
                f"Total：**{result}**{compare_text}"
            )
        else:
            output = (
                f"{message.author.mention}\n"
                f"{display_expr}\n"
                f"Total：**{result}**{compare_text}"
            )

        await message.channel.send(output)

    except Exception as e:
        await message.channel.send(f"Error: {e}")

bot.run(TOKEN)
