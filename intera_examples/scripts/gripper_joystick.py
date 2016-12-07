#!/usr/bin/env python

# Copyright (c) 2013-2016, Rethink Robotics
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
# 3. Neither the name of the Rethink Robotics nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

"""
SDK Gripper Example: joystick
"""
import argparse

import rospy

import intera_interface
import intera_external_devices


def map_joystick(joystick, limb):
    """
    maps joystick input to gripper commands

    @param joystick: an instance of a Joystick
    """
    print("Getting robot state... ")
    rs = intera_interface.RobotEnable(intera_interface.CHECK_VERSION)
    init_state = rs.state()
    try:
        gripper = intera_interface.Gripper(limb)
    except ValueError:
        rospy.logerr("Could not detect a gripper attached to the robot.")
        return
    
    def clean_shutdown():
        print("\nExiting example...")
        if not init_state:
            print("Disabling robot...")
            rs.disable()
    rospy.on_shutdown(clean_shutdown)

    # decrease position dead_zone
    gripper.set_dead_zone(2.5)

    # abbreviations
    jhi = lambda s: joystick.stick_value(s) > 0
    jlo = lambda s: joystick.stick_value(s) < 0
    bdn = joystick.button_down
    bup = joystick.button_up

    def print_help(bindings_list):
        print("Press Ctrl-C to quit.")
        for bindings in bindings_list:
            for (test, _cmd, doc) in bindings:
                if callable(doc):
                    doc = doc()
                print("%s: %s" % (str(test[1]), doc))

    def offset_position(offset):
        current = gripper.get_position()
        set_position = min(gripper.MAX_POSITION,
                          max(gripper.MIN_POSITION,
                             current + offset))
        gripper.set_position(set_position)

    def offset_holding(offset):
        current = gripper.get_force()
        print("Current force {0}".format(current))
        holding_force = min(gripper.MAX_FORCE,
                           max(gripper.MIN_FORCE,
                              current + offset))
        gripper.set_holding_force(holding_force)

    num_steps = 10.0
    position_step = (gripper.MAX_POSITION - gripper.MIN_POSITION) / num_steps
    force_step = (gripper.MAX_FORCE - gripper.MIN_FORCE) / num_steps
    bindings_list = []
    bindings = (
        #(test, command, description)
        ((bdn, ['btnLeft']), (gripper.reboot, []), "reboot"),
        ((bdn, ['btnUp']), (gripper.calibrate, []), "calibrate"),
        ((bdn, ['leftTrigger']), (gripper.close, []), "close"),
        ((bup, ['leftTrigger']), (gripper.open, []), "open (release)"),
        ((bdn, ['leftBumper']), (gripper.stop, []), "stop"),
        ((jlo, ['leftStickVert']), (offset_position, [-position_step]),
                                    "decrease position"),
        ((jhi, ['leftStickVert']), (offset_position, [position_step]),
                                     "increase position"),
        ((jlo, ['rightStickVert']), (offset_holding, [-force_step]),
                                    "decrease holding force"),
        ((jhi, ['rightStickVert']), (offset_holding, [force_step]),
                                    "increase holding force"),
        ((bdn, ['function1']), (print_help, [bindings_list]), "help"),
        ((bdn, ['function2']), (print_help, [bindings_list]), "help"),
    )
    bindings_list.append(bindings)

    rospy.loginfo("Enabling robot...")
    rs.enable()
    rate = rospy.Rate(100)
    print_help(bindings_list)
    print("Press <Start> button for help; Ctrl-C to stop...")
    while not rospy.is_shutdown():
        # test each joystick condition and call binding cmd if true
        for (test, cmd, doc) in bindings:
            if test[0](*test[1]):
                cmd[0](*cmd[1])
                print(doc)
        rate.sleep()
    rospy.signal_shutdown("Example finished.")


def main():
    """SDK Gripper Example: Joystick Control

    Use a game controller to control the grippers.

    Attach a game controller to your dev machine and run this
    example along with the ROS joy_node to control gripper
    using the joysticks and buttons. Be sure to provide
    the *joystick* type you are using as an argument to setup
    appropriate key mappings.

    Uses the intera_interface.Gripper class and the helper classes
    in intera_external_devices.Joystick.
    """
    epilog = """
See help inside the example with the "Start" button for controller
key bindings.
    """
    rp = intera_interface.RobotParams()
    valid_limbs = rp.get_limb_names()
    if not valid_limbs:
        rp.log_message(("Cannot detect any limb parameters on this robot. "
                        "Exiting."), "ERROR")
        return
    arg_fmt = argparse.RawDescriptionHelpFormatter
    parser = argparse.ArgumentParser(formatter_class=arg_fmt,
                                     description=main.__doc__,
                                     epilog=epilog)
    required = parser.add_argument_group('required arguments')
    required.add_argument(
        '-j', '--joystick', required=True, choices=['xbox', 'logitech', 'ps3'],
        help='specify the type of joystick to use'
    )
    parser.add_argument(
        "-l", "--limb", dest="limb", default=valid_limbs[0],
        choices=valid_limbs,
        help="Limb on which to run the gripper joystick example"
    )
    args = parser.parse_args(rospy.myargv()[1:])

    joystick = None
    if args.joystick == 'xbox':
        joystick = intera_external_devices.joystick.XboxController()
    elif args.joystick == 'logitech':
        joystick = intera_external_devices.joystick.LogitechController()
    elif args.joystick == 'ps3':
        joystick = intera_external_devices.joystick.PS3Controller()
    else:
        # Should never reach this case with proper argparse usage
        parser.error("Unsupported joystick type '%s'" % (args.joystick))

    print("Initializing node... ")
    rospy.init_node("sdk_gripper_joystick")

    map_joystick(joystick, args.limb)


if __name__ == '__main__':
    main()
