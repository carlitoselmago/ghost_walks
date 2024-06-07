import pymysql
import pymysql.cursors
import numpy as np
import time
import logging

class db():

    limitrows=1000

    params={"host":'localhost',
            "user":'ghost',
            "password":'walks',
         "database":'ghostwalks'}

    def __init__(self,presencemult=1,blocksize=0.2):

        # Connect to the database
        self.conn = pymysql.connect(host=self.params["host"],user=self.params["user"],password=self.params["password"],database=self.params["database"])
        #cursorclass=pymysql.cursors.DictCursor)
      
        self.cursor=self.conn.cursor()
        self.presencemult=presencemult
        self.blocksize=blocksize
    
    def insertPos(self, tagid, x, y):
   
        conn=self.conn = pymysql.connect(host=self.params["host"],user=self.params["user"],password=self.params["password"],database=self.params["database"])
        cursor = conn.cursor()
        value = 1.0
        sql = "INSERT INTO `positions` (`tagname`, `x`, `y`, `amount`) VALUES (%s, %s, %s, %s)"
        
        try:
            # Insert the main position
            cursor.execute(sql, (tagid, x, y, value))

            # Insert positions in a ring around the main position
            rings = 2
            for r in range(rings):
                d = self.blocksize * r
                u = value / (r + 2)
                positions = [
                    (x - d, y + d, u), (x, y + d, u), (x + d, y + d, u),
                    (x + d, y, u), (x + d, y - d, u), (x, y - d, u),
                    (x - d, y - d, u), (x - d, y, u)
                ]

                for pos in positions:
                    cursor.execute(sql, (tagid, *pos))

            conn.commit()
        except pymysql.MySQLError as e:
            logging.error(f"SQL Error: {e}")
            conn.rollback()
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            conn.rollback()
        finally:
            cursor.close()

    def getHeatMapData(self):
        sql="SELECT "

    def getNormValue(self,x,y):
       
        #get total count
        sql = "SELECT SUM(amount) as count FROM positions;"
        self.cursor.execute(sql)
        result = self.cursor.fetchone()
        total=result["count"]
        #get specific area count
        sql = "SELECT SUM(amount) as count FROM `positions` WHERE `x`>"+str(x-self.blocksize)+" AND `x`<"+str(x+self.blocksize)+" AND `y`>"+str(y-self.blocksize)+" AND `y`<"+str(y+self.blocksize)+";"

        self.cursor.execute(sql)
        result = self.cursor.fetchone()
        #print("result",result)
        if result:
            local=result["count"]
            if local==None:
                local=0.0
        else:
            local=0.0

        #print("total",total,"local",local)
        if total==0 or local==0:
            return 0.0

        
        norm=(local/total)
        #print("norm",norm)
       
        return norm
    
    def getPresenceValue(self,x,y):
        conn=self.conn = pymysql.connect(host=self.params["host"],user=self.params["user"],password=self.params["password"],database=self.params["database"])
        cursor=conn.cursor()
        sql = "SELECT SUM(amount) as count FROM `positions` WHERE `x`>"+str(x-self.blocksize)+" AND `x`<"+str(x+self.blocksize)+" AND `y`>"+str(y-self.blocksize)+" AND `y`<"+str(y+self.blocksize)+" LIMIT "+str(self.limitrows)+";"  
        cursor.execute(sql)
        result = cursor.fetchone()
        #print("result",result)
        if result:
            local=result[0]#result["count"]
            if local==None:
                local=0.0
        else:
            local=0.0

        result=local*self.presencemult
        if result>1.0:
            result=1.0
        #print("result",result)
        
        return result
        
    def generateHeatMapMatrix(self,anchor_positions, sizeX, sizeY):
        """
        Generate a heatmap matrix with normalized values.

        :param sizeX: Number of columns in the heatmap.
        :param sizeY: Number of rows in the heatmap.
        :return: A 2D numpy array representing the heatmap.
        """
        # Determine the boundaries based on anchor points
        min_x = min(anchor_positions.values(), key=lambda pos: pos[0])[0]
        min_y = min(anchor_positions.values(), key=lambda pos: pos[1])[1]
        max_x = max(anchor_positions.values(), key=lambda pos: pos[0])[0]
        max_y = max(anchor_positions.values(), key=lambda pos: pos[1])[1]
        
        # Calculate the step size in meters for each cell in the heatmap
        step_x = (max_x - min_x) / (sizeX - 1) if sizeX > 1 else 0
        step_y = (max_y - min_y) / (sizeY - 1) if sizeY > 1 else 0

        heatmap = np.zeros((sizeY, sizeX))

        for i in range(sizeY):
            for j in range(sizeX):
                x = min_x + j * step_x
                y = min_y + i * step_y
                heatmap[i, j] = self.getPresenceValue(x, y)
        #time.sleep(0.001)
        return heatmap