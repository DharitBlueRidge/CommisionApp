import pandas as pd

def calculate_daily_sales_bonus(daily_sales):
    if daily_sales >= 2500:
        return 400
    elif daily_sales >= 2000:
        return 250
    elif daily_sales >= 1500:
        return 150
    elif daily_sales >= 1100:
        return 100
    return 0

def calculate_stretch_bonus(monthly_sales):
    if monthly_sales >= 30000:
        return 1500
    elif monthly_sales >= 25000:
        return 1000
    return 0

def calculate_product_commission(profit_per_unit, quantity):
    return (profit_per_unit * quantity) * 0.10

def calculate_service_commission(service_sales):
    return service_sales * 0.10

def calculate_referral_bonus(new_clients):
    return new_clients * 20

def calculate_review_bonus(reviews, min_reviews_per_week=3):
    # Assuming a 4-week month for simplicity
    if reviews >= min_reviews_per_week * 4:
        return reviews * 10
    return 0
