import pandas as pd

def calculate_daily_sales_bonus(daily_sales):
    """
    Returns the bonus amount based on daily sales.
    AED 1,100 = 100
    AED 1,500 = 150 (extra 50)
    AED 2,000 = 250 (extra 100)
    AED 2,500+ = 400 (extra 150)
    """
    if daily_sales >= 2500:
        return 400
    elif daily_sales >= 2000:
        return 250
    elif daily_sales >= 1500:
        return 150
    elif daily_sales >= 1100:
        return 100
    return 0

def calculate_weekly_bonus_eligibility(weekly_sales):
    """
    *** Minimum AED 4,500 total sales per week to earn any of the above bonuses
    """
    return weekly_sales >= 4500

def calculate_stretch_bonus(monthly_sales):
    """
    If the Total monthly sales reaches AED 25,000 monthly sales = then an extra AED 1000 is earned
    AED 30,000+ monthly sales = extra AED 1500
    """
    if monthly_sales >= 30000:
        return 1500
    elif monthly_sales >= 25000:
        return 1000
    return 0

def calculate_product_commission(profit_per_unit, quantity):
    """
    10% commission on Product sales, calculated from the Profit, not the revenue
    (Sell price – Cost Price)*10%
    """
    return (profit_per_unit * quantity) * 0.10

def calculate_service_commission(service_sales):
    """
    10% commission on the Sales of a specific service
    """
    return service_sales * 0.10

def calculate_referral_bonus(new_clients):
    """
    AED 20 for every new client referral
    """
    return new_clients * 20

def calculate_review_bonus(reviews_count, week_num):
    """
    AED 10 for every 5-star review (min 3 reviews/week)
    The bonus is only paid if the stylist achieves at least 3 reviews in a given week.
    """
    if reviews_count >= 3:
        return reviews_count * 10
    return 0
