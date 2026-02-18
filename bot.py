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
    if n <= 0 or m <= 0:
        raise ValueError("n and m must be positive")
    if n > 100:
        raise ValueError("n must be <= 100")
    if m > 1000:
        raise ValueError("m must be <= 1000")
    return [random.randint(1, int(m)) for _ in range(int(n))]

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if not message.content.startswith("!r "):
        return

    expr = message.content[3:].strip()

    try:
        comparison_match = re.search(r"(>=|<=|==|=|>|<)", expr)
        comparator = None
        compare_value = None

        if comparison_match:
            comparator = comparison_match.group()
            left, right = expr.split(comparator, 1)
            compare_value = safe_eval(right)
            expr = left.strip()

        display_parts = []

        dice_pattern = r"(\d+)([db])(\d+)"

        while True:
            match = re.search(dice_pattern, expr)
            if not match:
                break

            n_expr, mode, m_expr = match.groups()
            n = int(n_expr)
            m = int(m_expr)

            rolls = roll_dice(n, m)

            if mode == "d":
                total = sum(rolls)
                roll_text = "+".join(str(r) for r in rolls)
                display_parts.append(f"{n_expr}d{m_expr}({roll_text})")
                expr = expr[:match.start()] + str(total) + expr[match.end():]

            else:
                remaining_expr = expr[match.end():]
                new_values = []
                for r in rolls:
                    temp_expr = str(r) + remaining_expr
                    val = safe_eval(temp_expr)
                    new_values.append(val)

                display_parts.append(
                    f"{n_expr}b{m_expr}({','.join(str(r) for r in new_values)})"
                )

                breakdown = new_values
                expr = None
                break

        if expr is not None:
            result = round(safe_eval(expr), 3)
            display_formula = " + ".join(display_parts)

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

                msg = (
                    f"{display_formula}\n"
                    f"Total: {result}\n"
                    f"Result: {'Success' if success else 'Fail'}"
                )
            else:
                msg = f"{display_formula}\nTotal: {result}"

        else:
            breakdown = [round(x, 3) for x in breakdown]
            display_formula = display_parts[0]

            if comparator:
                success_count = 0
                for v in breakdown:
                    if comparator in ["=", "=="] and v == compare_value:
                        success_count += 1
                    elif comparator == ">" and v > compare_value:
                        success_count += 1
                    elif comparator == "<" and v < compare_value:
                        success_count += 1
                    elif comparator == ">=" and v >= compare_value:
                        success_count += 1
                    elif comparator == "<=" and v <= compare_value:
                        success_count += 1

                msg = (
                    f"{display_formula}\n"
                    f"Success Count: {success_count}"
                )
            else:
                msg = f"{display_formula}"

        await message.channel.send(f"{message.author.mention}\n{msg}")

    except Exception as e:
        await message.channel.send(f"Error: {e}")

bot.run(TOKEN)
