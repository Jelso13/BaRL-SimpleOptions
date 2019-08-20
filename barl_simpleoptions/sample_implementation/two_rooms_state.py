from barl_simpleoptions import State

class TwoRoomsState(State) :
    
    gridworld = [
            [0,0,0,1,0,0,0], # 0 is floor.
            [0,0,0,0,0,0,0], # 1 is wall.
            [0,0,0,1,0,0,0]  # Top-left (0,0) is initial state.
        ]                    # Bottom-right (2,6) is terminal goal state.

    def __init__(self, pos = (0,0)) :
        self.pos = pos

    def __str__(self) :
        return str("({},{})".format(*self.pos))
    
    def __hash__(self):
        return hash(str(self))

    def __eq__(self, other_state) :
        return self.pos == other_state.pos

    def get_available_actions(self) :       
        available_actions = []
        y, x = self.pos
        
        # Can we move North?
        if ((y - 1 >= 0) and (self.gridworld[y - 1][x] == 0)) :
            available_actions.append("N")
        # Can we move South?
        if ((y + 1 <= 2) and (self.gridworld[y + 1][x] == 0)) :
            available_actions.append("S")
        # Can we move West?
        if ((x - 1 >= 0) and (self.gridworld[y][x - 1] == 0)) :
            available_actions.append("W")
        # Can we move East?
        if ((x + 1 <= 6) and (self.gridworld[y][x + 1] == 0)) :
            available_actions.append("E")

        return available_actions

    def take_action(self, action) :
        y, x, = self.pos

        if (action == "N") :
            return [TwoRoomsState((y - 1, x))]
        elif (action == "S") :
            return [TwoRoomsState((y + 1, x))]
        elif (action == "W") :
            return [TwoRoomsState((y, x - 1))]
        elif (action == "E") :
            return [TwoRoomsState((y, x + 1))]

    def is_action_legal(self, action) :
        return action in self.get_available_actions()

    def is_state_legal(self) :
        y, x = self.pos
        
        # Is the y position outside of the gridworld bounds?
        if (y < 0 or y > 2) :
            return False

        # Is the x position outside of the gridworld bounds?
        if (x < 0 or x > 6) :
            return False

        # Is the position inside a wall?
        if (self.gridworld[y][x] == 1) :
            return False

        # If all checks have been passed, this must be a valid state!
        return True

    def is_initial_state(self) :
        if (self.pos == (0,0)) :
            return True
        else :
            return False
    
    def is_terminal_state(self) :
        if (self.pos == (2,6)) :
            return True
        else :
            return False

    def get_successors(self) :
        action_successors = [self.take_action(action) for action in self.get_available_actions()]
        return  list(set().union(*action_successors))