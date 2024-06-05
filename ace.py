#!/usr/bin/python3

import argparse

from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from time import sleep

from env import Credentials as C

CENTRAL_PARK_LINK = "https://www.nycgovparks.org/tennisreservation/availability/12"
CENTRAL_PARK_ID = 12
CENTRAL_PARK_WINDOW = 30

MCCARREN_PARK_ID = 11
MCCARREN_PARK_WINDOW = 7

ID_TO_WINDOW = {
    CENTRAL_PARK_ID: CENTRAL_PARK_WINDOW,
    MCCARREN_PARK_ID: MCCARREN_PARK_WINDOW,
}


def log(*content):
    print("[", datetime.now(), "]", *content)


def get_driver():
    options = webdriver.ChromeOptions()
    user_agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.50 Safari/537.36"
    options.add_argument(f"user-agent={user_agent}")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--allow-running-insecure-content")
    options.add_argument("--headless")
    return webdriver.Chrome(options=options)


def get_id(link):
    parts = link.split("/")
    return int(parts[-1])


def get_window(link):
    return ID_TO_WINDOW[id]


def get_input(driver, id):
    return driver.find_element(by=By.XPATH, value=f"//input[@id='{id}']")


def fill_player_info(driver, court_id):
    num_players = get_input(driver, "num_players_2")
    num_players.click()

    sleep(0.5)

    if court_id == CENTRAL_PARK_ID:
        permit_number = get_input(driver, "permit-number1")
        permit_number.send_keys(C.permit_number)

        name = get_input(driver, "name1")
        name.send_keys(C.name)
    else:
        num_permits = get_input(driver, "single_play_exist_1")
        num_permits.click()

        name = get_input(driver, "name")
        name.send_keys(C.name)

    email = get_input(driver, "email")
    email.send_keys(C.email)

    address = get_input(driver, "address")
    address.send_keys(C.address)

    city = get_input(driver, "city")
    city.send_keys(C.city)

    zip_code = get_input(driver, "zip")
    zip_code.send_keys(C.zip_code)

    phone = get_input(driver, "phone")
    phone.send_keys(C.phone)


def fill_payment_info(driver):
    cc_number = get_input(driver, "cc_number")
    cc_number.send_keys(C.cc_number)

    exp_month = get_input(driver, "expdate_month")
    exp_month.send_keys(C.exp_month)

    exp_year = get_input(driver, "expdate_year")
    exp_year.send_keys(C.exp_year)

    csc = get_input(driver, "cvv2_number")
    csc.send_keys(C.csc)


def get_available_courts(driver, date, time):
    date_table = driver.find_element(by=By.ID, value=date)
    time_row = date_table.find_element(
        by=By.XPATH, value=f".//tr[td[strong[contains(text(), '{time}')]]]"
    )
    return time_row.find_elements(by=By.CLASS_NAME, value="status2")


def get_link(court):
    return court.find_element(by=By.XPATH, value=".//a").get_attribute("href")


def click_button(driver, value):
    button = driver.find_element(
        by=By.XPATH,
        value=f"//input[@value='{value}']",
    )
    button.click()
    sleep(0.5)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "-l",
        "--link",
        default=CENTRAL_PARK_LINK,
    )
    ap.add_argument("-t", "--time", default="12:00 p.m.")
    ap.add_argument("-b", "--book", action="store_true")
    ap.add_argument("-i", "--id", type=int)
    ap.add_argument("-d", "--dates", nargs="+")
    args = ap.parse_args()

    log("==========Starting up==========")
    driver = get_driver()
    try:
        driver.get(args.link)
    except Exception as e:
        log(f"Unable to load {args.link}")
        log(e)
        exit()

    # Wait for page load
    sleep(1)

    # Set rebook state
    rebook = "rebookcp" in args.link or "rainedout" in args.link
    if rebook:
        log("Rebook mode on")
        assert args.id, "Need to provide court id for rebooking"
    elif not args.id:
        args.id = get_id(args.link)

    dates = args.dates
    if not dates:
        window = ID_TO_WINDOW[args.id]
        next_date = datetime.now() + timedelta(days=window)
        dates = [datetime.strftime(next_date, "%Y-%m-%d")]

    log(f"Searching for courts on {', '.join(dates)} at {args.time}")

    for date in dates:
        reserved = False

        try:
            log("Trying", date)
            courts = get_available_courts(driver, date, args.time)
        except Exception as e:
            log(f"Unable find available courts")
            log(e)
            continue

        if not courts:
            log("No courts found.")
            continue

        log(f"Found {len(courts)} courts")

        for link in [get_link(court) for court in courts]:
            try:
                log("Trying", link)
                driver.get(link)
                sleep(0.5)

                if rebook:
                    # Rebook doesn't need player details
                    if args.book:
                        click_button(driver, "Make Reservation")
                        log("Successfully booked")
                    reserved = True
                    break

                # Fill player details
                click_button(driver, "Confirm and Enter Player Details")
                fill_player_info(driver, args.id)
                click_button(driver, "Continue to Payment")
                sleep(3)

                # Switch to payment iframe
                driver.switch_to.frame(3)
                fill_payment_info(driver)

                if args.book:
                    click_button(driver, "Pay Now")
                    log("Successfully booked")
                reserved = True
                break
            except Exception as e:
                log(f"Error booking {link}")
                log(e)

                driver.get_screenshot_as_file("error.png")
                continue

        if reserved:
            break

    if not reserved:
        log("No bookings made")
        exit()

    sleep(3)
    driver.get_screenshot_as_file("success.png")
    driver.close()
    log("Done")


if __name__ == "__main__":
    main()
